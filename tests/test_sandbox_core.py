"""Unit tests for SandboxRunner core execution engine."""

import time

from src.models.models_public import SandboxConfig
from src.sandbox.core import SandboxRunner


def test_basic_execution() -> None:
    """Verify that a simple Python snippet executes and captures stdout."""
    config = SandboxConfig(max_execution_time_seconds=5)
    with SandboxRunner(config) as runner:
        result = runner.execute("print('Hello from Sandbox!')")
        assert result.success is True
        assert "Hello from Sandbox!" in result.stdout
        assert result.is_final_answer is False
        assert result.error is None


def test_state_persistence_across_executions() -> None:
    """Verify variables and state persist between consecutive calls."""
    config = SandboxConfig(max_execution_time_seconds=5)
    with SandboxRunner(config) as runner:
        # Step 1: Define variable and function
        res1 = runner.execute(
            "counter = 10\n"
            "def double(v):\n"
            "    return v * 2"
        )
        assert res1.success is True

        # Step 2: Use previously defined variable and function
        res2 = runner.execute(
            "counter = double(counter)\n"
            "print(counter)"
        )
        assert res2.success is True
        assert "20" in res2.stdout


def test_final_answer_interception() -> None:
    """Verify that final_answer() signals task completion with solution."""
    config = SandboxConfig(max_execution_time_seconds=5)
    with SandboxRunner(config) as runner:
        code = (
            "solution = 'def solve(): return 42'\n"
            "final_answer(solution)"
        )
        result = runner.execute(code)
        assert result.success is True
        assert result.is_final_answer is True
        assert result.final_answer_value == "def solve(): return 42"


def test_custom_tools_namespace() -> None:
    """Verify tools provided in tools_namespace are callable in sandbox."""
    def custom_add(a: int, b: int) -> int:
        return a + b

    config = SandboxConfig(max_execution_time_seconds=5)
    tools = {"custom_add": custom_add}
    with SandboxRunner(config, tools_namespace=tools) as runner:
        result = runner.execute(
            "res = custom_add(15, 27)\n"
            "print(f'Sum: {res}')"
        )
        assert result.success is True
        assert "Sum: 42" in result.stdout


def test_output_truncation() -> None:
    """Verify output exceeding 4000 characters is truncated with notice."""
    config = SandboxConfig(max_execution_time_seconds=5)
    with SandboxRunner(config) as runner:
        # Generate 6000 characters of output
        result = runner.execute("print('A' * 6000)")
        assert result.success is True
        assert result.truncated is True
        assert "Tool output was truncated due to size limits" in result.output
        assert result.output.startswith("A" * 4000)


def test_execution_timeout_and_worker_recovery() -> None:
    """Verify runaway loops trigger timeout and allow subsequent calls."""
    config = SandboxConfig(max_execution_time_seconds=1)
    with SandboxRunner(config) as runner:
        # Runaway loop exceeding 1 second
        start = time.perf_counter()
        result = runner.execute("while True:\n    pass")
        elapsed = time.perf_counter() - start

        assert result.success is False
        assert "Execution hit the timeout" in (result.error or "")
        assert elapsed >= 1.0

        # Verify that runner recovered and executes subsequent code cleanly
        recovery_result = runner.execute("print('Alive again!')")
        assert recovery_result.success is True
        assert "Alive again!" in recovery_result.stdout


def test_error_traceback_capture() -> None:
    """Verify unhandled exceptions produce structured error traces."""
    config = SandboxConfig(max_execution_time_seconds=5)
    with SandboxRunner(config) as runner:
        result = runner.execute("1 / 0")
        assert result.success is False
        assert result.error is not None
        assert "ZeroDivisionError" in result.error
        assert "[error]" in result.output


def test_reset_clears_namespace() -> None:
    """Verify that reset() clears user-defined variables from memory."""
    config = SandboxConfig(max_execution_time_seconds=5)
    with SandboxRunner(config) as runner:
        runner.execute("temp_var = 999")
        runner.reset()
        res = runner.execute("print(temp_var)")
        assert res.success is False
        assert "NameError" in (res.error or "")
