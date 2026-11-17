"""Application agent_swebench entry point for Agent Smith."""

import sys
from src.core.logger import get_logger
from src.core.exceptions import AgentSmithException

logger = get_logger(__name__)


def main() -> int:
    """Execute agent_swebench entry point and return process exit code."""

    try:
        #         Parser les arguments CLI (via argparse) :
        # --task-file <chemin>
        # --output <chemin> (destination de solution.json)
        # --model-name <nom>
        # --provider-url <url>
        # Charger la tâche SWEBenchTaskInput
        # Appeler l'agent correspondant SWEBenchAgent
        #  et sauvegarder le SolutionOutput dans le fichier demandé.
        logger.info("Main function launched!")
        return 0

    except AgentSmithException as err:
        logger.error(f"Handled agent error: {err}")
        return 1

    except (KeyboardInterrupt):
        logger.warning("Execution interrupted by user or system.")
        # TODO: Nettoyage Docker ici
        return 130

    except Exception:
        logger.exception("Unexpected unhandled crash occurred.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
