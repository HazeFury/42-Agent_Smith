"""Unit tests for the centralized logging module (src/core/logger.py)."""

import logging
import sys
import pytest

from src.core.logger import get_logger, setup_agent_logging


@pytest.fixture(autouse=True)
def reset_logging() -> None:
    """Reset root agent_smith handlers before each test run."""
    root_agent_logger = logging.getLogger("agent_smith")
    root_agent_logger.handlers.clear()


def test_logger_hierarchy_and_name() -> None:
    """Verify child loggers attach correctly to agent_smith root."""
    setup_agent_logging()

    # Case 1: Standard module path prefixed with 'src.'
    logger1 = get_logger("src.sandbox.fs_guard")
    assert logger1.name == "agent_smith.sandbox.fs_guard"

    # Case 2: Module path without 'src.'
    logger2 = get_logger("core.loop")
    assert logger2.name == "agent_smith.core.loop"

    # Case 3: Module path already prefixed
    logger3 = get_logger("agent_smith.mcp.client")
    assert logger3.name == "agent_smith.mcp.client"


def test_logger_writes_to_stderr_and_not_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify logs emit exclusively to sys.stderr and keep stdout empty."""
    setup_agent_logging(level="INFO")
    logger = get_logger("tests.sample_module")

    test_message = "Test log on stderr - stdout must remain clean"
    logger.info(test_message)

    captured = capsys.readouterr()

    # sys.stdout must be strictly empty (evaluation constraint)
    assert captured.out == "", "Error: logs were detected on sys.stdout!"

    # sys.stderr must contain formatted log output
    assert test_message in captured.err
    assert "agent_smith.tests.sample_module" in captured.err
    assert "INFO" in captured.err


def test_lazy_initialization() -> None:
    """Verify get_logger auto-initializes without explicit setup call."""
    root_agent_logger = logging.getLogger("agent_smith")
    root_agent_logger.handlers.clear()

    # Call get_logger directly without prior setup_agent_logging invocation
    logger = get_logger("isolated_test")
    assert logger.name == "agent_smith.isolated_test"

    # Handlers must be configured automatically on root logger
    assert len(root_agent_logger.handlers) > 0
    assert isinstance(root_agent_logger.handlers[0], logging.StreamHandler)
    assert root_agent_logger.handlers[0].stream == sys.stderr
