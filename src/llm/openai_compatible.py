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

from src.llm.base import BaseLLMClient


class OpenAICompatibleClient(BaseLLMClient):
    pass

# appel HTTP POST sur {base_url}/chat/completions,
# gestion de stop_sequences, calcul de latency_ms
# et des tokens.
