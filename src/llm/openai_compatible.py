# Que vous appeliez Groq, OpenRouter, Together AI, Mistral, DeepSeek ou un modèle local (Ollama) : 👉 La réponse JSON a TOUJOURS la même structure constante :

# json
# {
#   "choices": [
#     {
#       "message": {
#         "content": "Voici le code généré..."   <-- Toujours ce chemin exact !
#       }
#     }
#   ],
#   "usage": {
#     "prompt_tokens": 142,                     <-- Toujours ce nom exact !
#     "completion_tokens": 58                   <-- Toujours ce nom exact !
#   }
# }

from src.llm.base import BaseLLMClient, LLMResponse
from typing import Any


class OpenAICompatibleClient(BaseLLMClient):
    def __init__(self, model_name: str, base_url: str, api_key: str) -> None:
        super().__init__(model_name=model_name, base_url=base_url, api_key=api_key)

    async def generate(
            self,
            messages: list[dict[str, Any]],
            stop_sequences: list[str] | None = None) -> LLMResponse:


# appel HTTP POST sur {base_url}/chat/completions,
# gestion de stop_sequences, calcul de latency_ms
# et des tokens.
