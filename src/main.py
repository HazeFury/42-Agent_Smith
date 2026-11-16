"""Application main entry point for Agent Smith."""

import sys
from src.core.logger import setup_agent_logging, get_logger
from src.core.exceptions import AgentSmithException

logger = get_logger(__name__)


def main() -> int:
    """Execute main entry point and return process exit code."""

    setup_agent_logging("INFO")

    try:
        logger.info("Main function launched!")
        return 0

    except AgentSmithException as err:
        logger.error(f"Handled agent error: {err}")
        return 1

    except (KeyboardInterrupt, SystemExit):
        logger.warning("Execution interrupted by user or system.")
        # TODO: Nettoyage Docker ici si SWE-bench
        return 130

    except Exception:
        logger.exception("Unexpected unhandled crash occurred.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
