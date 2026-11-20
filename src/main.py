"""Application main entry point for Agent Smith."""

import asyncio
import os
from dotenv import load_dotenv
from src.core.exceptions import AgentSmithException
from src.core.extraction import CodeExtractor
from src.core.logger import get_logger
from src.core.loop import AgentLoop
from src.core.prompt import PromptManager
from src.llm.openai_compatible import OpenAICompatibleClient
from src.models.models_public import SandboxConfig
from src.sandbox import SandboxRunner

load_dotenv()
logger = get_logger(__name__)

TASK_PROMPT = (
    "Write a Python function `add(a, b)` that returns the sum of two "
    "numbers. Submit it with final_answer."
)


async def test_loop() -> None:
    keys_str = os.getenv("GEMINI_API_KEYS", "")
    api_key = keys_str.split(",")[0].strip().strip('"')

    # The sandbox worker is a fork: create it before the HTTP client so it
    # does not inherit open connections.
    sandbox = SandboxRunner(SandboxConfig())
    llm_client = OpenAICompatibleClient(
        model_name="gemini-3.1-flash-lite",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        api_key=api_key,
    )
    agent = AgentLoop(llm_client, sandbox, CodeExtractor(), PromptManager())

    try:
        print("Running the agent loop...")
        output = await agent.run("test-1", "mbpp", TASK_PROMPT)
    except AgentSmithException as err:
        logger.error(f"Agent loop failed: {err}")
        return
    finally:
        sandbox.close()
        await llm_client.aclose()

    print(f"\nsuccess={output.success} iterations={output.iterations}")
    print(
        f"tokens: in={output.total_input_tokens} "
        f"out={output.total_output_tokens} "
        f"time={output.total_time_seconds:.1f}s"
    )
    for step in output.steps:
        print(f"\n--- step {step.step} ({step.model_name}) ---")
        print("LLM output:\n", step.llm_output)
        print("Sandbox input:\n", step.sandbox_input)
        print("Sandbox output:\n", step.sandbox_output)
    print("\n--- solution ---")
    print(output.solution)


if __name__ == "__main__":
    asyncio.run(test_loop())


# import sys
# from src.core.logger import get_logger
# from src.core.exceptions import AgentSmithException

# logger = get_logger(__name__)


# def main() -> int:
#     """Execute main entry point and return process exit code."""

#     try:
#         logger.info("Main function launched!")
#         return 0

#     except AgentSmithException as err:
#         logger.error(f"Handled agent error: {err}")
#         return 1

#     except (KeyboardInterrupt, SystemExit):
#         logger.warning("Execution interrupted by user or system.")
#         # TODO: Nettoyage Docker ici si SWE-bench
#         return 130

#     except Exception:
#         logger.exception("Unexpected unhandled crash occurred.")
#         return 1


# if __name__ == "__main__":
#     sys.exit(main())
