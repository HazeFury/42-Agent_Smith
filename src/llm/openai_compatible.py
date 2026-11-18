"""OpenAI-compatible LLM client implementation.

This module provides a unified client for any provider adhering to the
standard OpenAI REST API specification (/chat/completions), including:
- Groq
- OpenRouter
- NVIDIA NIM (build.nvidia.com)
- Together AI
- Mistral AI
- Local runners (vLLM, Ollama)

All providers share the exact same JSON request and response contract:
- Request: POST {base_url}/chat/completions with "model", "messages", "stop"
- Response: { "choices": [{ "message": { "content": ... } }], "usage": ... }
"""

import time
from typing import Any
import httpx

from src.core.exceptions import AgentSmithException, LLMQuotaExhaustedError
from src.llm.base import BaseLLMClient, LLMResponse


class OpenAICompatibleClient(BaseLLMClient):
    """Client for LLM providers implementing the OpenAI chat completion API."""

    def __init__(self, model_name: str, base_url: str, api_key: str) -> None:
        """Initialize the client with model identifier and credentials.

        Args:
            model_name: Target model identifier (e.g. 'llama-3.1-8b-instant').
            base_url: Provider base endpoint (e.g. 'https://api.groq.com').
            api_key: Secret API token for authentication.
        """
        super().__init__(
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
        )

    async def generate(
        self,
        messages: list[dict[str, Any]],
        stop_sequences: list[str] | None = None,
    ) -> LLMResponse:
        """Send chat messages via an HTTP POST following the OpenAI standard.

        Executes an asynchronous POST request to `{base_url}/chat/completions`
        formatted according to the official OpenAI API specification:
        - Payload: `{"model": ..., "messages": [...], "stop": [...]}`
        - Headers: `Authorization: Bearer <token>`, `Content-Type: json`

        Monitors response latency, extracts token consumption, detects HTTP 429
        quota exhaustion, and returns a standardized `LLMResponse`.

        Args:
            messages: List of chat message dicts with 'role' and 'content'.
            stop_sequences: Optional tokens halting generation early.

        Returns:
            Standardized LLMResponse with generated text and usage metrics.

        Raises:
            LLMQuotaExhaustedError: On HTTP 429 (Rate limit / quota exhausted).
            AgentSmithException: On any other network or HTTP API failure.
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
        }
        if stop_sequences:
            payload["stop"] = stop_sequences

        start_time: float = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    url=url,
                    headers=headers,
                    json=payload,
                )
        except httpx.TimeoutException as err:
            raise AgentSmithException(
                f"Request to {self.model_name} timed out after 60s: {err}"
            ) from err
        except httpx.RequestError as err:
            raise AgentSmithException(
                f"Network communication failure with {self.base_url}: {err}"
            ) from err

        if response.status_code == 429:
            raise LLMQuotaExhaustedError(
                f"Quota exhausted on {self.model_name}: {response.text}"
            )
        if response.status_code != 200:
            raise AgentSmithException(
                f"HTTP {response.status_code} error from {self.model_name}: "
                f"{response.text}"
            )

        request_time_ms = (time.perf_counter() - start_time) * 1000
        response_data = response.json()

        text = response_data["choices"][0]["message"]["content"]
        usage = response_data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        return LLMResponse(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            request_time_ms=request_time_ms,
            api_url=self.base_url,
            model_name=self.model_name,
        )
