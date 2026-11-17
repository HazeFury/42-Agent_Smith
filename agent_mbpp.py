"""Application agent_mbpp entry point for Agent Smith."""

import sys
from src.core.logger import get_logger
from src.core.exceptions import AgentSmithException

logger = get_logger(__name__)


def main() -> int:
    """Execute agent_mbpp entry point and return process exit code."""

    try:
        #         Parser les arguments CLI (via argparse) :
        # --task-file <chemin>
        # --output <chemin> (destination de solution.json)
        # --model-name <nom>
        # --provider-url <url>
        # Charger la tâche MBPPTaskInput
        # Appeler l'agent correspondant MBPPAgent
        #  et sauvegarder le SolutionOutput dans le fichier demandé.

        logger.info("agent_mbpp launched!")
        return 0

    except AgentSmithException as err:
        logger.error(f"Handled agent error: {err}")
        return 1

    except (KeyboardInterrupt):
        logger.warning("Execution interrupted by user or system.")
        # TODO: Tuer les sous-processus de test en cours
        return 130

    except Exception:
        logger.exception("Unexpected unhandled crash occurred.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
