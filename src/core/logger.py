"""Centralized logging module for Agent Smith.

This module guarantees:
- Strict output redirection to sys.stderr to preserve sys.stdout for evaluation
  harnesses and stdio protocols.
- Hierarchical logger naming to accurately pinpoint the origin of every event.
- Lazy auto-initialization when setup_agent_logging is not explicitly invoked.
"""

import logging
import sys


def setup_agent_logging(level: str = "INFO") -> None:
    """Configure the root 'agent_smith' project logger to emit on sys.stderr.

    This function should be called once at application entry points
    (e.g., main.py, agent_mbpp.py, agent_swebench.py, sandbox CLI).

    Args:
        level: Minimum log level string ('DEBUG', 'INFO', 'WARNING', 'ERROR').
    """
    logger = logging.getLogger("agent_smith")

    if not logger.handlers:
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        logger.setLevel(numeric_level)

        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Do not propagate to root logger to prevent duplicated messages
        logger.propagate = False


def get_logger(module_name: str) -> logging.Logger:
    """Return a child logger attached to the 'agent_smith' hierarchy.

    Recommended usage across modules:
        from src.core.logger import get_logger
        logger = get_logger(__name__)

    Args:
        module_name: Originating module name (pass '__name__').

    Returns:
        Configured and typed logging.Logger instance.
    """
    if not logging.getLogger("agent_smith").handlers:
        setup_agent_logging()

    clean_name = module_name.removeprefix("src.")

    if not clean_name.startswith("agent_smith"):
        full_name = f"agent_smith.{clean_name}"
    else:
        full_name = clean_name

    return logging.getLogger(full_name)
