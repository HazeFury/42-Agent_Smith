"""Application main entry point for Agent Smith."""

import asyncio
import os
from dotenv import load_dotenv

from src.llm.openai_compatible import OpenAICompatibleClient

load_dotenv()


async def test_llm():
    keys_str = os.getenv("GROCK_API_KEYS", "")
    api_key = keys_str.split(",")[0].strip().strip('"')

    client = OpenAICompatibleClient(
        model_name="openai/gpt-oss-120b",
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
    )

    messages = [
        {
            "role": "user",
            "content": "Écris une fonction Python simple qui additionne deux nombres."
        }
    ]

    print("Request s...")
    response = await client.generate(messages)

    print("Model name:", response.model_name)
    print("Response time :", f"{response.request_time_ms:.1f} ms")
    print("Token:", f"Input: {response.input_tokens} | Output: {response.output_tokens}")
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
