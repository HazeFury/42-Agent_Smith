"""Package d'abstraction LLM, résilience et métrologie.

Ce dossier gère les interactions avec les modèles de langage distants et la
tolérance aux pannes sur les quotas gratuits (Section V.6) :
- base.py              : Interface abstraite BaseLLMClient et modèle de réponse
                         LLMResponse.
- openai_compatible.py : Client unifié pour tous les fournisseurs compatibles
                         avec l'API OpenAI /v1/chat/completions (OpenRouter,
                         Groq, Mistral, Together).
- gemini.py            : Client adapté aux spécificités de l'API Google AI
                         Studio / Gemini.
- key_manager.py       : Pool multi-tokens par fournisseur, détection des
                         codes HTTP 429 et bascule automatique de clé
                         (rotation).
- token_tracker.py     : Mesure précise de la latence (wall-clock ms) et
                         décompte des tokens consommés (input/output) pour les
                         StepMetrics.
"""
