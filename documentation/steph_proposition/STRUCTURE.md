# Arborescence Consolidée — Agent Smith (Version Fusionnée)

Ce document présente la version finale et consolidée de l'arborescence du projet **Agent Smith**, issue de la fusion des deux propositions initiales. La structure de base est celle de **Marco (TREE.md)**, enrichie des apports de **Steph** là où ils corrigent des faiblesses identifiées. Chaque modification est documentée et justifiée.

---

## 1. Arborescence Finale

```text
agent_smith/
├── .env.example                     # Modèle des variables d'environnement (clés API)
├── .gitignore                       # Exclusion des caches, .env, venv, conteneurs
├── pyproject.toml                   # Métadonnées du projet, dépendances uv et scripts CLI
├── uv.lock                          # Verrouillage déterministe des dépendances
├── README.md                        # Documentation officielle en anglais (Chapitre VII)
├── BENCHMARK_REPORT.md              # Rapport officiel de comparaison des modèles (Chapitre V.7)
├── sandbox_template.json            # Configuration par défaut du bac à sable (JSON)
│
├── agent_mbpp.py                    # Point d'entrée CLI MBPP — classe MBPPAgentApp
├── agent_swebench.py                # Point d'entrée CLI SWE-bench — classe SWEBenchAgentApp
├── mcp_tools_mbpp.py                # Serveur MCP pour MBPP (imposé à la racine) — MBPPMCPServer
├── mcp_tools_swebench.py            # Serveur MCP pour SWE-bench (imposé à la racine) — SWEBenchMCPServer
│
├── benchmark_artifacts/             # Traces structurées des benchmarks (preuves solution.json)
│   ├── sympy__sympy-14711/
│   │   ├── llama-3.1-8b_solution.json
│   │   └── ...
│   └── ...
│
├── evaluations/                     # Sorties brutes des runs de la moulinette
│   └── .gitkeep
│
├── tests/                           # Tests unitaires et d'intégration
│   ├── test_sandbox_security.py     # Tests d'intrusion de la sandbox (100% requis)
│   ├── test_llm_rotation.py         # Tests de rotation de clés et tolérance aux pannes
│   ├── test_code_extractor.py       # Tests d'extraction de code (Python, XML, JSON, ReAct)
│   ├── test_mcp_tools.py            # Tests unitaires des 9 outils obligatoires
│   └── test_mbpp_loop.py            # Test d'intégration de la boucle agentique
│
└── src/                             # Code source modulaire du projet
    ├── __init__.py
    │
    ├── core/                        # Moteur de raisonnement et infrastructure transversale
    │   ├── __init__.py
    │   ├── loop.py                  # AgentLoop — boucle Thought → Code → Observation
    │   ├── prompt.py                # PromptManager — system prompt et formatage observations
    │   ├── extraction.py            # CodeExtractor — conversion multi-formats en code Python
    │   ├── exceptions.py            # Hiérarchie AgentSmithException et sous-classes typées
    │   └── logger.py                # setup_logging() — journalisation orientée sys.stderr
    │
    ├── agent/                       # Orchestrateurs spécialisés par benchmark
    │   ├── __init__.py
    │   ├── mbpp_agent.py            # MBPPAgent — chargement tâche, boucle et SolutionOutput
    │   └── swebench_agent.py        # SWEBenchAgent — chargement tâche, Docker et patch git
    │
    ├── models/                      # Modèles de données Pydantic v2 (contrats stricts)
    │   ├── __init__.py
    │   ├── config.py                # SandboxConfig — allowlists, timeout, quotas RAM
    │   ├── tasks.py                 # MBPPTaskInput, SWEBenchTaskInput
    │   └── metrics.py               # StepMetrics, SolutionOutput
    │
    ├── sandbox/                     # Moteur d'exécution sécurisé — un fichier par verrou
    │   ├── __init__.py
    │   ├── core.py                  # SandboxRunner — exécution en sous-processus isolé
    │   ├── security.py              # Analyse AST statique avant exécution (imports, traversal)
    │   ├── builtins_guard.py        # Assainissement du dict __builtins__ (eval, exec, compile...)
    │   ├── fs_guard.py              # open() sécurisé — restriction aux allowed_directories
    │   ├── limits.py                # Quotas mémoire (setrlimit) et timeout (SIGALRM/process kill)
    │   └── cli.py                   # SandboxCLIApp — REPL interactif `uv run sandbox`
    │
    ├── mcp/                         # Client et bridge Model Context Protocol
    │   ├── __init__.py
    │   ├── client.py                # MCPClient — sessions stdio et HTTP SSE
    │   ├── bridge.py                # Injection des outils MCP comme fonctions Python dans la sandbox
    │   └── dynamic_manual.py        # Génération dynamique du manuel d'outils pour le prompt LLM
    │
    ├── llm/                         # Abstraction des LLM et gestion des quotas
    │   ├── __init__.py
    │   ├── base.py                  # BaseLLMClient (ABC) et LLMResponse (BaseModel)
    │   ├── openai_compatible.py     # OpenAICompatibleClient — Groq, OpenRouter, Mistral, Together
    │   ├── gemini.py                # GeminiClient — Google AI Studio / Gemini API
    │   ├── key_manager.py           # KeyManager — pool de clés, détection 429, rotation
    │   └── token_tracker.py         # TokenTracker — comptage tokens et mesure latences
    │
    └── tools/                       # Implémentation des outils métier par domaine
        ├── __init__.py
        ├── file_tools.py            # read_file (cat -n), edit_file, list_files
        ├── search_tools.py          # search_code, search_definitions, find_references
        ├── execution_tools.py       # run_tests, run_command, get_patch
        ├── mbpp_tools.py            # MBPPToolKit — run_tests(code, test_list)
        └── docker_manager.py        # DockerManager — cycle de vie conteneurs SWE-bench
```

---

## 2. Modifications par rapport à TREE.md et leurs Justifications

### 2.1. Ajout de `src/core/` — Moteur de Raisonnement et Infrastructure Transversale
> **Source** : Steph | **Modifie** : `src/agent/` dans Marco

**Ce qui change** : Les fichiers `loop.py`, `prompt_builder.py` et `code_extractor.py` de Marco restaient dans `src/agent/`, un package à double responsabilité (raisonnement + orchestration spécialisée). La proposition Steph les déplace dans un package `core/` dédié.

**Justification** :
- `AgentLoop`, `PromptManager` et `CodeExtractor` sont **agnostiques du benchmark** (MBPP ou SWE-bench). Les placer dans `src/agent/` induisait une confusion conceptuelle.
- `src/core/` incarne clairement le **moteur de raisonnement commun**, tandis que `src/agent/` conserve uniquement les **orchestrateurs spécialisés** (`mbpp_agent.py`, `swebench_agent.py`). La séparation est nette et lisible.
- Cela facilite la réutilisation : un troisième benchmark futur hériterait du `core/` sans toucher à `agent/`.

---

### 2.2. Ajout de `src/core/exceptions.py` et `src/core/logger.py`
> **Source** : Steph | **Absents** : Dans TREE.md de Marco

**Ce qui change** : Marco ne prévoyait aucun fichier pour la gestion des exceptions ni pour la journalisation. Ces composants auraient probablement atterri par défaut dans `loop.py`, créant un fichier trop chargé.

**Justification** :
- `exceptions.py` centralise la hiérarchie `AgentSmithException → SandboxSecurityError, SandboxTimeoutError, LLMQuotaExhaustedError...`. Sans ce fichier, les `except` risquent d'intercepter des signaux système (`SystemExit`, `KeyboardInterrupt`) — une **faute critique** pour le sujet (Section IV.1).
- `logger.py` contenant `setup_logging()` garantit que **tous les logs transitent par `sys.stderr`** et jamais par `stdout`, ce qui est impératif pour ne pas polluer les sorties de la moulinette.
- Ces deux fichiers sont fréquemment ciblés lors de la soutenance (*"Que se passe-t-il si votre API rate-limite ?"*). Avoir un fichier dédié permet de répondre en l'ouvrant directement.

---

### 2.3. Découpage du LLM — `base.py` de Steph + `key_manager.py`/`token_tracker.py` de Marco
> **Source** : Hybride | **Remplace** : Les sous-classes par provider de Marco et le fichier unique chez Steph

**Ce qui change** :
- **Gardé de Marco** : séparation de la gestion des clés (`key_manager.py`) du comptage des métriques (`token_tracker.py`).
- **Gardé de Steph** : un seul `openai_compatible.py` générique pour Groq, OpenRouter, Mistral, Together (pas de sous-classes par provider) + `base.py` explicite avec `BaseLLMClient(ABC)`.
- **Supprimé de Marco** : le sous-dossier `providers/` avec `openrouter.py`, `groq.py`, etc. — ces APIs partagent exactement le même format JSON, créer des sous-classes est du sur-engineering.

**Justification** :
- `key_manager.py` gère l'état de rotation (quelle clé est active, laquelle est en cooldown) → objet **stateful**.
- `token_tracker.py` mesure les latences et décompte les tokens → responsabilité de **métrologie**, distincte de la résilience.
- Mélanger les deux dans un seul fichier `token_manager.py` mélangeait deux responsabilités bien différentes.

---

### 2.4. Découpage des outils en 3 fichiers thématiques + `docker_manager.py` isolé
> **Source** : Marco pour l'organisation, Steph pour `mbpp_tools.py`

**Ce qui change** : Marco propose déjà `file_tools.py`, `search_tools.py`, `execution_tools.py` et `docker_manager.py`. La seule addition de Steph est `mbpp_tools.py`.

**Justification** :
- `docker_manager.py` isolé de `SWEBenchAgent` : la gestion Docker est un composant **infrastructure** complexe (démarrage, montage de volumes, nettoyage sur SIGTERM), testable indépendamment de la boucle agent.
- `mbpp_tools.py` : l'outil `run_tests(code, test_list)` MBPP a des besoins différents des outils SWE-bench (il n'a pas de `TESTBED_PATH`, il évalue directement du code Python). Le séparer évite une conditionnelle dans le code des outils.

---

### 2.5. Conservation des deux répertoires `benchmark_artifacts/` et `evaluations/`
> **Source** : Hybride (Steph + Marco)

**Ce qui change** : Steph avait `benchmark_artifacts/`, Marco avait `evaluations/`. Les deux sont conservés car ils ont des rôles distincts.

**Justification** :
- `benchmark_artifacts/` : stockage structuré et **permanent** des `solution.json` produits lors de la campagne de benchmark officielle (5 modèles × 3 tâches). Committé dans le dépôt comme preuve d'évaluation.
- `evaluations/` : répertoire de **travail quotidien** pour les sorties brutes des runs de test avec la moulinette. Non-commité (`.gitignore`) pour ne pas polluer l'historique git avec des fichiers de débogage.

---
