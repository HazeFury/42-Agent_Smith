"""Application main entry point for Agent Smith."""

import asyncio
import os
from dotenv import load_dotenv
from src.core.exceptions import AgentSmithException
from src.core.logger import get_logger

from src.llm.openai_compatible import OpenAICompatibleClient

load_dotenv()
logger = get_logger(__name__)


async def test_llm() -> None:
    keys_str = os.getenv("NVIDIA_API_KEYS", "")
    api_key = keys_str.split(",")[0].strip().strip('"')

    client = OpenAICompatibleClient(
        model_name="nvidia/nemotron-3.5-bolt-e4b",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
    )

    messages = [
        {
            "role": "user",
            "content": (
                "Écris une fonction Python simple qui additionne deux nombres."
            )
        }
    ]

    try:
        print("Request s...")
        response = await client.generate(messages)
    except AgentSmithException as err:
        logger.error(f"LLM request failed: {err}")
        return
    finally:
        await client.aclose()

    print("Model name:", response.model_name)
    print("Response time :", f"{response.request_time_ms:.1f} ms")
    print(
        "Token:",
        f"Input: {response.input_tokens} | Output: {response.output_tokens}",
    )
    print("URL:", response.api_url)
    print("\n--- Generated content ---")
    print(response.text)


if __name__ == "__main__":
    asyncio.run(test_llm())


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
