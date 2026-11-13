"""Unit tests for exception hierarchy and system signal propagation."""

import pytest

from src.core.exceptions import (
    AgentSmithException,
    CodeExtractionError,
    LLMQuotaExhaustedError,
    MaxIterationsReachedError,
    MCPCommunicationError,
    SandboxMemoryError,
    SandboxSecurityError,
    SandboxTimeoutError,
    TaskValidationError,
    TokenLimitExceededError,
)


def test_system_signals_do_not_inherit_from_agent_smith_exception() -> None:
    """Verify system signals are strictly outside AgentSmithException tree."""
    assert not issubclass(KeyboardInterrupt, AgentSmithException)
    assert not issubclass(SystemExit, AgentSmithException)


def test_custom_exceptions_inherit_from_agent_smith_exception() -> None:
    """Verify all domain errors properly inherit from AgentSmithException."""
    subclasses = [
        TaskValidationError,
        CodeExtractionError,
        SandboxSecurityError,
        SandboxTimeoutError,
        SandboxMemoryError,
        MCPCommunicationError,
        LLMQuotaExhaustedError,
        TokenLimitExceededError,
        MaxIterationsReachedError,
    ]
    for cls in subclasses:
        assert issubclass(cls, AgentSmithException)


def test_keyboard_interrupt_bypasses_agent_smith_exception() -> None:
    """Verify KeyboardInterrupt is NOT caught by except AgentSmithException."""
    caught_as_agent_error = False

    with pytest.raises(KeyboardInterrupt):
        try:
            raise KeyboardInterrupt()
        except AgentSmithException:
            caught_as_agent_error = True

    assert not caught_as_agent_error, (
        "KeyboardInterrupt was masked by AgentSmithException!"
    )


def test_system_exit_bypasses_agent_smith_exception() -> None:
    """Verify SystemExit is NOT caught by except AgentSmithException."""
    caught_as_agent_error = False

    with pytest.raises(SystemExit):
        try:
            raise SystemExit(1)
        except AgentSmithException:
            caught_as_agent_error = True

    assert not caught_as_agent_error, (
        "SystemExit was masked by AgentSmithException!"
    )


def test_child_exceptions_are_caught_by_parent_handler() -> None:
    """Verify polymorphic catch: AgentSmithException catches any child."""
    caught_child_names = []

    test_instances = [
        SandboxSecurityError("Access denied to /etc"),
        SandboxTimeoutError("30s exceeded"),
        LLMQuotaExhaustedError("Rate limited on all keys"),
    ]

    for error_instance in test_instances:
        try:
            raise error_instance
        except AgentSmithException as caught:
            caught_child_names.append(caught.__class__.__name__)

    assert caught_child_names == [
        "SandboxSecurityError",
        "SandboxTimeoutError",
        "LLMQuotaExhaustedError",
    ]


def test_exception_string_representation() -> None:
    """Verify string formatting follows [ClassName] message convention."""
    err = SandboxSecurityError("Unauthorized file open")
    assert str(err) == "[SandboxSecurityError] Unauthorized file open"
