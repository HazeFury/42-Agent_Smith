"""Core execution engine for the sandboxed execution environment.

Provides SandboxRunner, which manages a persistent worker process communicating
over an IPC pipe. This persistent process preserves namespace variables across
multiple execution cycles (for both the agent loop and the interactive REPL)
while enforcing wall-clock timeouts and output length constraints.
"""

from __future__ import annotations

import contextlib
import io
import multiprocessing
import multiprocessing.connection
import multiprocessing.process
import time
import traceback
from typing import Any

from src.core.exceptions import FinalAnswerSignal
from src.models.models_private import ExecutionResult
from src.models.models_public import SandboxConfig


def _execute_code_in_worker(
    code: str,
    worker_globals: dict[str, Any],
) -> dict[str, Any]:
    """Execute code snippet inside the worker process and return data.

    Captures stdout and stderr via StringIO, intercepts FinalAnswerSignal to
    detect task completion, and catches uncaught exceptions to format traces.
    """
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    start_time = time.perf_counter()

    success = True
    is_final_answer = False
    final_answer_value: str | None = None
    error_msg: str | None = None

    try:
        compiled_code = compile(code, "<sandbox>", "exec")
        with contextlib.redirect_stdout(stdout_buf):
            with contextlib.redirect_stderr(stderr_buf):
                exec(compiled_code, worker_globals)
    except FinalAnswerSignal as signal:
        is_final_answer = True
        final_answer_value = signal.answer
        success = True
    except SystemExit as exc:
        success = False
        error_msg = f"SystemExit: {exc.code}"
    except KeyboardInterrupt:
        # Re-raise KeyboardInterrupt to respect control-flow signals
        raise
    except BaseException:
        success = False
        error_msg = traceback.format_exc()

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    stdout_str = stdout_buf.getvalue()
    stderr_str = stderr_buf.getvalue()

    # Compose output text for the caller / agent
    output_parts: list[str] = []
    if stdout_str:
        output_parts.append(stdout_str)
    if stderr_str:
        output_parts.append(f"[stderr]\n{stderr_str}")
    if error_msg:
        output_parts.append(f"[error]\n{error_msg}")

    output_str = "\n".join(output_parts)

    return {
        "stdout": stdout_str,
        "stderr": stderr_str,
        "output": output_str,
        "success": success,
        "is_final_answer": is_final_answer,
        "final_answer_value": final_answer_value,
        "execution_time_ms": elapsed_ms,
        "error": error_msg,
    }


def _worker_entrypoint(
    conn: multiprocessing.connection.Connection,
    config: SandboxConfig,
    tools_namespace: dict[str, Any] | None,
) -> None:
    """Entrypoint function executed in the isolated child worker process.

    Maintains a persistent worker_globals namespace between successive
    EXECUTE commands so variables and imports persist across agent steps
    and REPL commands.
    """

    def final_answer(answer: Any) -> None:
        """Native sandbox construct allowing agent to signal completion."""
        raise FinalAnswerSignal(str(answer))

    worker_globals: dict[str, Any] = {
        "__name__": "__main__",
        "__doc__": None,
        "final_answer": final_answer,
    }

    if tools_namespace:
        for name, tool in tools_namespace.items():
            worker_globals[name] = tool

    while True:
        try:
            if not conn.poll(None):
                break
            message = conn.recv()
        except (EOFError, KeyboardInterrupt):
            break

        cmd = message.get("cmd")
        if cmd == "EXECUTE":
            code = message.get("code", "")
            try:
                res = _execute_code_in_worker(code, worker_globals)
                conn.send({"status": "OK", "data": res})
            except KeyboardInterrupt:
                break
            except Exception as exc:
                conn.send({"status": "ERROR", "error": str(exc)})
        elif cmd == "RESET":
            worker_globals = {
                "__name__": "__main__",
                "__doc__": None,
                "final_answer": final_answer,
            }
            if tools_namespace:
                for name, tool in tools_namespace.items():
                    worker_globals[name] = tool
            conn.send({"status": "OK"})
        elif cmd == "SHUTDOWN":
            break


class SandboxRunner:
    """Manages sandboxed code execution inside a persistent worker process.

    Attributes:
        config: SandboxConfig with resource constraints and allowlists.
        tools_namespace: Dict of tools injected into the sandbox namespace.
    """

    def __init__(
        self,
        config: SandboxConfig,
        tools_namespace: dict[str, Any] | None = None,
    ) -> None:
        """Initialize SandboxRunner and start persistent worker process."""
        self.config = config
        self.tools_namespace = dict(tools_namespace) if tools_namespace else {}
        self._mp_context = multiprocessing.get_context("fork")
        self._parent_conn: multiprocessing.connection.Connection | None = None
        self._worker_process: multiprocessing.process.BaseProcess | None = None
        self._start_worker()

    def _start_worker(self) -> None:
        """Start or restart persistent worker process and IPC pipe."""
        self._terminate_worker()
        parent_conn, child_conn = self._mp_context.Pipe(duplex=True)
        self._parent_conn = parent_conn

        process = self._mp_context.Process(
            target=_worker_entrypoint,
            args=(child_conn, self.config, self.tools_namespace),
            daemon=True,
        )
        process.start()
        # Close child copy in parent to allow proper EOF detection on crash
        child_conn.close()
        self._worker_process = process

    def _terminate_worker(self) -> None:
        """Terminate and clean up active worker process and IPC connection."""
        if self._parent_conn:
            try:
                self._parent_conn.close()
            except Exception:
                pass
            self._parent_conn = None

        if self._worker_process:
            if self._worker_process.is_alive():
                try:
                    self._worker_process.terminate()
                    self._worker_process.join(timeout=1.0)
                    if self._worker_process.is_alive():
                        self._worker_process.kill()
                        self._worker_process.join(timeout=1.0)
                except Exception:
                    pass
            self._worker_process = None

    def _truncate_output(
        self,
        text: str,
        max_chars: int = 4000,
    ) -> tuple[str, bool]:
        """Truncate output if it exceeds max_chars and append an explicit note.

        Args:
            text: Raw output string to inspect and potentially truncate.
            max_chars: Maximum allowed character length before truncation.

        Returns:
            tuple[str, bool]: (processed_text, was_truncated)
        """
        if len(text) <= max_chars:
            return text, False

        notice = (
            f"\n... [Tool output was truncated due to size limits: "
            f"showing first {max_chars} of {len(text)} characters] ..."
        )
        truncated_text = text[:max_chars] + notice
        return truncated_text, True

    def execute(self, code: str) -> ExecutionResult:
        """Execute a Python code string inside persistent sandbox worker.

        Args:
            code: Python source code string to execute.

        Returns:
            ExecutionResult with stdout, stderr, execution time, and status.
        """
        if not self._worker_process or not self._worker_process.is_alive():
            self._start_worker()

        assert self._parent_conn is not None

        start_time = time.perf_counter()
        timeout = float(self.config.max_execution_time_seconds)

        # Dispatch execution request to child process
        try:
            self._parent_conn.send({"cmd": "EXECUTE", "code": code})
        except (BrokenPipeError, OSError):
            self._start_worker()
            err_msg = "Pipe broken when dispatching execution."
            return ExecutionResult(
                stdout="",
                stderr="",
                output=f"[error]\n{err_msg}",
                success=False,
                is_final_answer=False,
                final_answer_value=None,
                truncated=False,
                execution_time_ms=0.0,
                error=err_msg,
            )

        # Poll with timeout to enforce max_execution_time_seconds
        has_data = self._parent_conn.poll(timeout)
        if not has_data:
            # Execution timed out: force terminate runaway worker and respawn
            self._terminate_worker()
            self._start_worker()
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            timeout_msg = (
                f"Execution hit the timeout ({timeout}s) and was terminated."
            )
            return ExecutionResult(
                stdout="",
                stderr="",
                output=f"[error]\n{timeout_msg}",
                success=False,
                is_final_answer=False,
                final_answer_value=None,
                truncated=False,
                execution_time_ms=elapsed_ms,
                error=timeout_msg,
            )

        # Retrieve response from child worker
        try:
            response = self._parent_conn.recv()
        except (EOFError, BrokenPipeError):
            self._terminate_worker()
            self._start_worker()
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            crash_msg = (
                "Sandbox worker process terminated unexpectedly during "
                "execution (e.g. fatal signal or memory exhaustion)."
            )
            return ExecutionResult(
                stdout="",
                stderr="",
                output=f"[error]\n{crash_msg}",
                success=False,
                is_final_answer=False,
                final_answer_value=None,
                truncated=False,
                execution_time_ms=elapsed_ms,
                error=crash_msg,
            )

        if response.get("status") != "OK":
            err = response.get("error", "Unknown worker error")
            return ExecutionResult(
                stdout="",
                stderr="",
                output=f"[error]\n{err}",
                success=False,
                is_final_answer=False,
                final_answer_value=None,
                truncated=False,
                execution_time_ms=(time.perf_counter() - start_time) * 1000.0,
                error=err,
            )

        data = response["data"]
        raw_output = data.get("output", "")
        truncated_output, was_truncated = self._truncate_output(raw_output)

        return ExecutionResult(
            stdout=data.get("stdout", ""),
            stderr=data.get("stderr", ""),
            output=truncated_output,
            success=data.get("success", True),
            is_final_answer=data.get("is_final_answer", False),
            final_answer_value=data.get("final_answer_value"),
            truncated=was_truncated,
            execution_time_ms=data.get("execution_time_ms", 0.0),
            error=data.get("error"),
        )

    def reset(self) -> None:
        """Reset the worker execution namespace to a clean state."""
        if (
            self._worker_process is not None
            and self._worker_process.is_alive()
            and self._parent_conn is not None
        ):
            try:
                self._parent_conn.send({"cmd": "RESET"})
                if self._parent_conn.poll(2.0):
                    self._parent_conn.recv()
                    return
            except Exception:
                pass
        self._start_worker()

    def close(self) -> None:
        """Cleanly shutdown worker process and release IPC resources."""
        if (
            self._worker_process is not None
            and self._worker_process.is_alive()
            and self._parent_conn is not None
        ):
            try:
                self._parent_conn.send({"cmd": "SHUTDOWN"})
                self._worker_process.join(timeout=0.5)
            except Exception:
                pass
        self._terminate_worker()

    def __enter__(self) -> SandboxRunner:
        """Enable context manager usage."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Ensure worker teardown on context exit."""
        self.close()
