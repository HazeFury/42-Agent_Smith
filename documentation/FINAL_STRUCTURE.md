```
agent_smith/
├── .env.example                     # Modèle des variables d'environnement (clés API)
├── .gitignore                       # Ignore .env, .venv, __pycache__, evaluations/, etc.
├── pyproject.toml                   # Config uv, Python 3.10, dépendances et entrypoint sandbox
├── uv.lock                          # Verrouillage déterministe des dépendances
├── README.md                        # Documentation officielle en anglais (norme 42)
├── BENCHMARK_REPORT.md              # Rapport de comparaison des 5 modèles sur SWE-bench
├── sandbox_template.json            # Configuration par défaut du bac à sable (JSON)
│
├── agent_mbpp.py                    # Point d'entrée racine : uv run python -m agent_mbpp ...
├── agent_swebench.py                # Point d'entrée racine : uv run python -m agent_swebench ...
├── mcp_tools_mbpp.py                # Serveur MCP MBPP (imposé à la racine par le sujet)
├── mcp_tools_swebench.py            # Serveur MCP SWE-bench (imposé à la racine par le sujet)
│
├── benchmark_artifacts/             # Fichiers solution.json officiels committés (preuves du rapport)
│   ├── task_1/
│   │   ├── model_a_solution.json
│   │   └── ...
│   └── ...
│
├── evaluations/                     # Sorties d'évaluation moulinette (ignoré par git)
│   └── .gitkeep
│
├── tests/                           # Suite de tests unitaires et d'intégration
│   ├── test_sandbox_security.py     # Vérification des verrous (import, builtins, paths, rlimit)
│   ├── test_code_extractor.py       # Validation extraction (Python, XML, Hermes JSON, ReAct)
│   ├── test_llm_rotation.py         # Test rotation de clés sur 429 et fallback
│   ├── test_mcp_tools.py            # Validation unitaire des outils filesystem/search/exec
│   ├── test_mbpp_loop.py            # Test d'intégration bout-en-bout MBPP
│   └── test_swebench_patch.py       # Test de conformité du git diff patch
│
└── src/
    ├── __init__.py
    │
    ├── models/                      # Modèles de données Pydantic v2 (contrats stricts)
    │   ├── __init__.py
    │   ├── config.py                # SandboxConfig (allowlists imports/paths, timeouts, RAM)
    │   ├── tasks.py                 # MBPPTaskInput, SWEBenchTaskInput
    │   └── metrics.py               # StepMetrics, SolutionOutput
    │
    ├── core/                        # Moteur agentique agnostique & utilitaires transversaux
    │   ├── __init__.py
    │   ├── loop.py                  # AgentLoop : boucle Thought → Code → Observation
    │   ├── extraction.py            # CodeExtractor : extraction et normalisation multi-formats
    │   ├── prompt.py                # PromptManager : assemblage prompts système et observations
    │   ├── exceptions.py            # Hiérarchie des erreurs (sans bloquer KeyboardInterrupt)
    │   └── logger.py                # Logger standardisé dirigé exclusivement vers sys.stderr
    │
    ├── agent/                       # Orchestrateurs applicatifs par benchmark
    │   ├── __init__.py
    │   ├── mbpp_agent.py            # MBPPAgent : pipeline complet tâche → loop → solution.json
    │   └── swebench_agent.py        # SWEBenchAgent : pipeline complet avec Docker & patch diff
    │
    ├── sandbox/                     # Environnement d'exécution sécurisé (1 fichier par verrou)
    │   ├── __init__.py
    │   ├── core.py                  # SandboxRunner : sous-processus isolé et primitive final_answer
    │   ├── security.py              # Analyse statique AST (filtrage imports & attributs dunder)
    │   ├── builtins_guard.py        # Dictionnaire __builtins__ assaini (sans eval, exec, compile)
    │   ├── fs_guard.py              # Wrapper open() avec résolution de liens canoniques (realpath)
    │   ├── limits.py                # resource.setrlimit (RAM), signal/timeout et coupure réseau
    │   └── cli.py                   # Mode REPL interactif (uv run sandbox)
    │
    ├── mcp/                         # Couche client Model Context Protocol & dynamic binding
    │   ├── __init__.py
    │   ├── client.py                # MCPClient : gestion sessions stdio et streamable HTTP (SSE)
    │   ├── dynamic_manual.py        # Générateur automatique du manuel d'outils pour le prompt LLM
    │   └── bridge.py                # Injection dynamique des outils MCP comme callables Python
    │
    ├── llm/                         # Abstraction LLM, résilience et métrologie
    │   ├── __init__.py
    │   ├── base.py                  # BaseLLMClient (ABC) et dataclass/model LLMResponse
    │   ├── openai_compatible.py     # Client unifié (Groq, OpenRouter, Mistral, Together)
    │   ├── gemini.py                # Client Google AI Studio / Gemini
    │   ├── key_manager.py           # Multi-token pool, détection 429 & rotation automatique
    │   └── token_tracker.py         # Décompte précis des tokens cumulés et mesure de latence
    │
    └── tools/                       # Implémentation concrète des outils métiers
        ├── __init__.py
        ├── file_tools.py            # read_file (format cat -n), edit_file, list_files
        ├── search_tools.py          # search_code, search_definitions, find_references
        ├── execution_tools.py       # run_tests, run_command, get_patch (git diff)
        ├── mbpp_tools.py            # MBPPToolKit : exécution isolée de run_tests(code, test_list)
        └── docker_manager.py        # Cycle de vie conteneurs Docker (démarrage, arrêt sur SIGTERM)
```