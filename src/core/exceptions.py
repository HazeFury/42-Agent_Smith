"""Centralized exception hierarchy for Agent Smith.
This module provides structured exception types that allow graceful error
handling across the agent loop, sandbox, MCP layer, and LLM providers without
masking critical system signals (KeyboardInterrupt, SystemExit).
"""


class AgentSmithException(Exception):
    """Base exception for all handled errors within Agent Smith."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return f"[{self.__class__.__name__}] {self.message}"


class CodeExtractionError(AgentSmithException):
    """Raised when no valid executable code block is found in LLM output."""


class TaskValidationError(AgentSmithException):
    """Raised when task.json fails schema validation or is malformed."""


class SandboxSecurityError(AgentSmithException):
    """Raised on security violation (forbidden import, bad path, network)."""


class SandboxTimeoutError(AgentSmithException):
    """Raised when sandbox execution exceeds max_execution_time_seconds."""


class SandboxMemoryError(AgentSmithException):
    """Raised when sandbox execution exceeds allowed RAM quota."""


class MCPCommunicationError(AgentSmithException):
    """Raised on connection failure, transport break, or RPC error in MCP."""


class LLMQuotaExhaustedError(AgentSmithException):
    """Raised when all provider API keys exhausted quota (429 rate limit)."""


class TokenLimitExceededError(AgentSmithException):
    """Raised when cumulative token usage exceeds the hard benchmark limit."""


class MaxIterationsReachedError(AgentSmithException):
    """Raised when the agent loop hits max_iterations without final_answer."""
