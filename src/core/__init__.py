"""Package du moteur agentique agnostique et composants transversaux.

Ce dossier centralise la logique commune indépendante du benchmark ciblé :
- loop.py       : Boucle maîtresse ReAct (Thought -> Code -> Observation).
- extraction.py : Extraction et conversion robuste du code généré par le LLM
                  (Markdown Python, XML Anthropic, JSON Hermes, ReAct).
- prompt.py     : Gestionnaire de prompts système, formatage des observations
                  et injection du manuel dynamique d'outils.
- exceptions.py : Hiérarchie centralisée des exceptions métier
                  (AgentSmithException, SandboxSecurityError, etc.) préservant
                  la propagation des signaux système (KeyboardInterrupt,
                  SystemExit).
- logger.py     : Configuration de la journalisation redirigée exclusivement
                  vers sys.stderr pour protéger les sorties de la moulinette.
"""
