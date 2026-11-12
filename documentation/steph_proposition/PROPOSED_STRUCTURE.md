# Synthèse de l'Arborescence du Projet (POO Pragmatique) — Agent Smith

Ce document présente l'arborescence consolidée et optimisée du projet **Agent Smith** (version 1.1). Elle élimine le sur-engineering (classes superflues, boilerplate Java-esque) tout en conservant une programmation orientée objet stricte, modulaire et hautement maintenable.

---

## 1. Arborescence Consolidée

```text
agent_smith/
├── pyproject.toml                     # Configuration uv, dépendances (pydantic, mcp, etc.), CLI scripts
├── uv.lock                            # Lockfile strict des dépendances uv
├── README.md                          # Documentation principale conforme aux exigences (Chapitre VII)
├── BENCHMARK_REPORT.md                # Rapport comparatif de 5 modèles x 2 providers x 3 tâches (Chapitre V.7)
├── sandbox_template.json              # Configuration Sandbox par défaut sérialisée (SandboxConfig)
│
├── mcp_tools_mbpp.py                  # [Requis racine] Serveur MCP MBPP (classe MBPPMCPServer)
├── mcp_tools_swebench.py              # [Requis racine] Serveur MCP SWE-bench (classe SWEBenchMCPServer)
├── agent_mbpp.py                      # Point d'entrée d'évaluation: `python -m agent_mbpp` (MBPPAgentApp)
├── agent_swebench.py                  # Point d'entrée d'évaluation: `python -m agent_swebench` (SWEBenchAgentApp)
│
├── benchmark_artifacts/               # Données sources et traces réelles des benchmarks (solution.json)
│   ├── swe_task_1/
│   │   ├── model_1_solution.json
│   │   └── ...
│   └── ...
│
├── src/                       # Package applicatif principal
│   ├── __init__.py
│   │
│   ├── core/                          # Cœur décisionnel et boucle agentique
│   │   ├── __init__.py
│   │   ├── loop.py                    # Boucle autonome Thought → Code → Observation (AgentLoop)
│   │   ├── prompt.py                  # Gestion unifiée des prompts et observations (PromptManager)
│   │   ├── extraction.py              # Parseur multi-formats (CodeExtractor, CodeExtractionResult)
│   │   ├── exceptions.py              # Hiérarchie d'exceptions typées (AgentSmithException)
│   │   └── logger.py                  # Initialisation du logging standard orienté vers stderr (setup_logging)
│   │
│   ├── models/                        # Modèles de données stricts Pydantic
│   │   ├── __init__.py
│   │   ├── metrics.py                 # StepMetrics, SolutionOutput (validés par la moulinette)
│   │   ├── sandbox.py                 # SandboxConfig (allowlists imports/chemins, quotas RAM, timeout)
│   │   └── tasks.py                   # MBPPTaskInput, SWEBenchTaskInput
│   │
│   ├── sandbox/                       # Environnement d'exécution sécurisé et REPL CLI
│   │   ├── __init__.py
│   │   ├── cli.py                     # CLI interactif conforme à `uv run sandbox` (SandboxCLIApp)
│   │   ├── runner.py                  # Exécution isolée, gestion du timeout 30s et de final_answer (SandboxRunner)
│   │   └── security.py                # Verrous stdlib pures : imports, builtins, réseau, mémoire (SecurityEnforcer)
│   │
│   ├── mcp/                           # Couche client MCP & introspection dynamique
│   │   ├── __init__.py
│   │   ├── client.py                  # Client MCP universel stdio et HTTP SSE (MCPClient)
│   │   └── tools.py                   # Découverte d'outils, wrapping Python et manuel LLM (MCPToolManager)
│   │
│   ├── tools/                         # Toolkits autonomes encapsulant les outils obligatoires
│   │   ├── __init__.py
│   │   ├── swebench.py                # Les 9 outils SWE-bench (SWEBenchToolKit)
│   │   └── mbpp.py                    # Outils de tests MBPP (MBPPToolKit)
│   │
│   └── llm/                           # Abstraction multi-fournisseurs et gestion des quotas
│       ├── __init__.py
│       ├── base.py                    # Interfaces abstraites BaseLLMClient & LLMResponse
│       ├── openai_compatible.py       # Client générique pour Groq, OpenRouter, Mistral, Together (OpenAICompatibleClient)
│       ├── gemini.py                  # Client dédié pour Google AI Studio / Gemini API (GeminiClient)
│       ├── token_manager.py           # Rotation dynamique des clés d'API anti-429 (TokenRotator)
│       └── router.py                  # Résilience, retries avec backoff et fallback (LLMRouter)
│
└── tests/                             # Suites de tests automatisées (Section VI)
    ├── __init__.py
    ├── test_sandbox_security.py       # Tests d'isolation (imports, builtins, réseau, quotas, signaux)
    ├── test_mcp_protocol.py           # Tests connexions stdio / HTTP et découverte dynamique
    ├── test_mandatory_tools.py        # Tests unitaires des 9 outils obligatoires (formats de sortie stricts)
    └── test_code_extraction.py        # Tests d'extraction multi-formats (Markdown, XML, Hermes JSON, ReAct)
```

---

## 2. Table des Responsabilités & Simplifications Apportées

| Composant | Classe / Module Principal | Simplification par rapport à la version sur-engineerée |
| :--- | :--- | :--- |
| **Outils SWE-bench** | `tools/swebench.py` (`SWEBenchToolKit`) | Regroupement des 9 outils obligatoires dans une classe unique au lieu de 3 services éclatés. |
| **Outils MBPP** | `tools/mbpp.py` (`MBPPToolKit`) | Module autonome simple pour `run_tests(code, test_list)`. |
| **Fournisseurs LLM** | `llm/openai_compatible.py` | 1 client paramétrable au lieu de multiplier les sous-classes clones (`groq.py`, `mistral.py`, `openrouter.py`). |
| **Client MCP & Outils** | `mcp/tools.py` (`MCPToolManager`) | Fusion du bridge de découverte et de la génération du manuel dans un gestionnaire unique. |
| **Prompts & Retours** | `core/prompt.py` (`PromptManager`) | Une classe unique pour générer le system prompt et formater les retours d'observation. |
| **Sandbox & Signal de Fin**| `sandbox/runner.py` | `FinalAnswerSignal` et l'injection du callable `final_answer` sont intégrés dans le runner sans fichier superflu. |
| **Journalisation** | `core/logger.py` (`setup_logging()`) | Configuration directe du standard `logging` de Python orienté sur `stderr`, élimination de la fausse `LoggerFactory`. |
| **Points d'Entrée CLI** | `agent_mbpp.py` & `agent_swebench.py` | Classes applicatives claires (`MBPPAgentApp`, `SWEBenchAgentApp`) gérant le cycle de vie et le nettoyage Docker. |
