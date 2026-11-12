# Cartes Trello — Agent Smith (Version Consolidée STRUCTURE.md)

Ce document fournit les **cartes Trello prêtes à l'emploi**, découpées selon la chronologie **MBPP First** en **4 Jalons (Sprints)** et strictement alignées sur l'arborescence de `STRUCTURE.md` et `ARCHITECTURE_SPEC.md`.

---

## 🎯 OBJECTIFS ET CRITÈRES GLOBAUX D'EXAMEN
- **MBPP** : 4/5 tâches réussies (*10 itérations max, 120s, 6k in, 1.5k out*).
- **SWE-bench** : 2/3 tâches réussies (*30 itérations max, 900s, 300k in, 10k out*).
- **Sandbox** : 100 % de réussite sur `exam_sandbox.sh`.

---

# 🟡 SPRINT 1 — MVP MBPP
> **Objectif du jalon** : `uv run python -m agent_mbpp` résout une première tâche algorithmique MBPP et produit un `solution.json` validé par la moulinette.
> **Point de convergence** : Dès le Jour 2 ou 3, les deux développeurs testent un run bout-en-bout.

---

### [S1-DEV1-01] SandboxRunner Minimal & final_answer
- **Développeur** : Dev 1
- **Fichier** : `src/sandbox/core.py`
- **Description** :
  Implémenter l'exécuteur de code Python dans un sous-processus isolé avec capture des flux I/O et construct de terminaison.
  - Définir `class FinalAnswerSignal(Exception)` avec l'attribut `answer: str`.
  - Définir `class ExecutionResult` avec champs : `stdout`, `stderr`, `exit_code`, `final_answer`, `is_timeout`, `is_truncated`.
  - Définir `class SandboxRunner.__init__(config: SandboxConfig, tools_namespace: dict)`.
  - Implémenter `SandboxRunner.execute(code: str) -> ExecutionResult` : exécution isolée, injection du callable `final_answer(answer_str)` qui lève `FinalAnswerSignal`.
  - Implémenter `SandboxRunner._truncate_output(text: str, max_chars: int = 4000) -> tuple[str, bool]`.
- **Critères d'acceptation** :
  - [ ] Le code `final_answer("42")` retourne `ExecutionResult.final_answer == "42"`.
  - [ ] Les appels `print("hello")` sont capturés dans `ExecutionResult.stdout`.
  - [ ] Une exception Python non gérée retourne `exit_code != 0` et le traceback dans `stderr`.
  - [ ] `KeyboardInterrupt` et `SystemExit` ne sont pas étouffés silencieusement.
  - [ ] Une sortie de plus de 4000 caractères est tronquée avec la mention `[TRUNCATED]`.

---

### [S1-DEV1-02] MBPPToolKit & Serveur MCP stdio
- **Développeur** : Dev 1
- **Fichiers** : `src/tools/mbpp_tools.py`, `mcp_tools_mbpp.py`
- **Description** :
  Créer l'outil MBPP et l'exposer via le protocole MCP en mode stdio à la racine du dépôt (*Section V.2.4*).
  - Dans `src/tools/mbpp_tools.py` : `class MBPPToolKit.run_tests(code: str, test_list: list[str]) -> str` évaluant les assertions et retournant `{"success": bool, "output": str}`.
  - Dans `mcp_tools_mbpp.py` : `class MBPPMCPServer` avec méthodes `register_tools()`, `run(transport="stdio")` et `@classmethod main()`.
- **Critères d'acceptation** :
  - [ ] `MBPPToolKit().run_tests("def add(a, b): return a + b", ["assert add(1, 2) == 3"])` retourne `{"success": true, "output": ""}`.
  - [ ] Une assertion fausse retourne `{"success": false, "output": "AssertionError..."}`.
  - [ ] `python mcp_tools_mbpp.py` démarre sans erreur en mode stdio.
  - [ ] Le serveur MCP répond correctement à une requête `tools/list` listant `run_tests`.

---

### [S1-DEV1-03] Client MCP stdio & Bridge Python
- **Développeur** : Dev 1
- **Fichiers** : `src/mcp/client.py`, `src/mcp/bridge.py`
- **Description** :
  Connecter la sandbox au serveur MCP local et transformer l'outil distant en fonction Python appelable.
  - Dans `src/mcp/client.py` : `class MCPClient` avec `connect_stdio(command: str)`, `list_tools()`, `call_tool(name, args)`, `close()`.
  - Dans `src/mcp/bridge.py` : `class MCPToolBridge.__init__(client: MCPClient)` avec `create_tool_callables() -> dict[str, Callable]`.
- **Critères d'acceptation** :
  - [ ] `MCPClient.connect_stdio("python mcp_tools_mbpp.py")` s'exécute sans erreur.
  - [ ] `list_tools()` retourne la définition de `run_tests`.
  - [ ] La fonction Python retournée par `MCPToolBridge` s'exécute de façon transparente à l'intérieur de `SandboxRunner`.

---

### [S1-DEV2-01] Modèles Pydantic : Tasks, Metrics & Config
- **Développeur** : Dev 2
- **Fichiers** : `src/models/config.py`, `src/models/tasks.py`, `src/models/metrics.py`
- **Description** :
  Définir les contrats de données Pydantic v2 imposés par le sujet et la moulinette (*Section V.1.1*).
  - `class SandboxConfig(BaseModel)` dans `src/models/config.py` : avec `is_import_authorized(module_name)` (gestion du wildcard `.*`), `is_path_authorized(path)` (`realpath`), et `from_json_file(path)`.
  - `class MBPPTaskInput(BaseModel)` dans `src/models/tasks.py` : `task_id`, `task_definition`, `function_definition`, `test_imports`, `test_list`.
  - `class StepMetrics(BaseModel)` et `class SolutionOutput(BaseModel)` dans `src/models/metrics.py` : avec méthodes `record_step(step)` et `to_file(path)`.
- **Critères d'acceptation** :
  - [ ] `SandboxConfig(...).is_import_authorized("collections.abc")` retourne `True` si `"collections.*"` est configuré.
  - [ ] `SandboxConfig(...).is_import_authorized("os")` retourne `False`.
  - [ ] `MBPPTaskInput.model_validate(json_data)` parse sans erreur les fichiers de tâches de la moulinette.
  - [ ] `SolutionOutput(...).to_file("solution.json")` génère un JSON valide avec tous les champs requis.

---

### [S1-DEV2-02] Client LLM OpenAI-Compatible & Extraction Markdown
- **Développeur** : Dev 2
- **Fichiers** : `src/llm/base.py`, `src/llm/openai_compatible.py`, `src/core/extraction.py`
- **Description** :
  Effectuer des requêtes aux modèles gratuits (Groq, OpenRouter) et extraire le code Python généré.
  - `class LLMResponse(BaseModel)` et `class BaseLLMClient(ABC)` dans `src/llm/base.py`.
  - `class OpenAICompatibleClient(BaseLLMClient)` dans `src/llm/openai_compatible.py` : appel HTTP sur `{base_url}/chat/completions` avec `stop_sequences`, calcul de `latency_ms` et des tokens.
  - `class CodeExtractor` dans `src/core/extraction.py` avec extraction des blocs Markdown ````python ... ````.
- **Critères d'acceptation** :
  - [ ] Une requête réelle sur Groq ou OpenRouter retourne une `LLMResponse` valide.
  - [ ] `LLMResponse.input_tokens > 0` et `LLMResponse.latency_ms > 0`.
  - [ ] `CodeExtractor.extract("```python\nprint(1)\n```")` extrait le code `print(1)`.
  - [ ] L'absence de bloc de code signale `was_malformed = True`.

---

### [S1-DEV2-03] AgentLoop MBPP & CLI agent_mbpp
- **Développeur** : Dev 2
- **Fichiers** : `src/core/prompt.py`, `src/core/loop.py`, `src/agent/mbpp_agent.py`, `agent_mbpp.py`
- **Description** :
  Assembler le cycle *Thought → Code → Observation*, l'orchestrateur `MBPPAgent` et le point d'entrée racine.
  - `class PromptManager` dans `src/core/prompt.py` : `build_system_prompt()` et `format_observation()`.
  - `class AgentLoop` dans `src/core/loop.py` : boucle autonome ReAct, limitation d'itérations, capture de `final_answer`.
  - `class MBPPAgent` dans `src/agent/mbpp_agent.py` : chargement tâche, instanciation loop, sauvegarde `solution.json`.
  - `class MBPPAgentApp` dans `agent_mbpp.py` : parsing CLI pour `uv run python -m agent_mbpp`.
- **Critères d'acceptation** :
  - [ ] `uv run python -m agent_mbpp --task-file task.json --output solution.json --model-name <name> --provider-url <url>` s'exécute de bout en bout.
  - [ ] Le fichier `solution.json` produit est validé avec succès par `uv run moulinette_eval validate mbpp task.json solution.json`.

---

# 🟠 SPRINT 2 — Sécurité Sandbox, Robustesse & 4/5 MBPP
> **Objectif du jalon** : 100 % de réussite à `exam_sandbox.sh`. L'agent résout au moins 4/5 tâches MBPP sans crash d'API ni dépassement de quotas.

---

### [S2-DEV1-01] Sécurité Sandbox Découpée (Pure Stdlib)
- **Développeur** : Dev 1
- **Fichiers** : `src/sandbox/security.py`, `src/sandbox/builtins_guard.py`, `src/sandbox/fs_guard.py`, `src/sandbox/limits.py`
- **Description** :
  Implémenter les 4 verrous d'isolation stricts sans aucune bibliothèque externe (pas de `RestrictedPython`).
  - Dans `src/sandbox/security.py` : `class ASTSecurityAnalyzer` rejetant via `ast.parse` les imports interdits et les accès aux attributs magiques (`__subclasses__`, etc.).
  - Dans `src/sandbox/builtins_guard.py` : `class BuiltinsGuard` assainissant le dictionnaire `__builtins__` (suppression `eval`, `exec`, `compile`).
  - Dans `src/sandbox/fs_guard.py` : `class FileSystemGuard` avec `safe_open()` restreignant les ouvertures de fichiers aux `allowed_directories`.
  - Dans `src/sandbox/limits.py` : `class ResourceLimits` neutralisant `socket.socket` (`PermissionError`) et appliquant les quotas RAM (`resource.setrlimit`).
- **Critères d'acceptation** :
  - [ ] `exec("import os")` est bloqué par l'analyseur AST.
  - [ ] `exec("open('/etc/shadow')")` lève `SandboxSecurityError`.
  - [ ] `exec("import socket; socket.socket()")` lève `PermissionError`.
  - [ ] `exec("eval('1+1')")` lève `NameError`.
  - [ ] Les tests d'isolation de `exam_sandbox.sh` passent avec succès.

---

### [S2-DEV1-02] Timeout Process & Manuel Dynamique MCP
- **Développeur** : Dev 1
- **Fichiers** : `src/sandbox/core.py` (enrichissement), `src/mcp/dynamic_manual.py`
- **Description** :
  Garantir la terminaison des boucles infinies à 30 secondes et générer la documentation Markdown dynamique des outils.
  - Dans `src/sandbox/core.py` : terminer de force le sous-processus via `terminate()` / `kill()` au bout de 30s (`max_execution_time_seconds`). Renseigner `ExecutionResult.is_timeout = True`.
  - Dans `src/mcp/dynamic_manual.py` : `class DynamicManualGenerator.generate(tools: list[MCPToolDefinition]) -> str` produisant la documentation Markdown à injecter dans le system prompt.
- **Critères d'acceptation** :
  - [ ] Un code `while True: pass` est tué en ≤ 32 secondes sans bloquer l'agent.
  - [ ] `ExecutionResult.is_timeout == True` sur timeout.
  - [ ] Le manuel généré liste fidèlement noms, signatures et descriptions des outils MCP connectés.

---

### [S2-DEV1-03] REPL CLI Sandbox (uv run sandbox)
- **Développeur** : Dev 1
- **Fichiers** : `src/sandbox/cli.py`, `pyproject.toml`
- **Description** :
  Implémenter le CLI interactif REPL conforme à la Section V.2.1 du sujet.
  - `class SandboxCLIApp` dans `src/sandbox/cli.py` : parsing arguments, initialisation sandbox/MCP, invite `>>> `, exécution de code utilisateur, sortie sur `exit` ou `Ctrl+D`.
  - Déclarer le script dans `pyproject.toml` : `[project.scripts] sandbox = "src.sandbox.cli:SandboxCLIApp.main"`.
- **Critères d'acceptation** :
  - [ ] La commande `uv run sandbox` ouvre le prompt interactif `>>> `.
  - [ ] `uv run sandbox sandbox_template.json --mcp-stdio "python mcp_tools_mbpp.py"` connecte les outils MBPP.
  - [ ] Taper `Ctrl+D` ou `exit` quitte proprement le programme avec le code 0.

---

### [S2-DEV2-01] Exceptions Centralisées & Logging stderr
- **Développeur** : Dev 2
- **Fichiers** : `src/core/exceptions.py`, `src/core/logger.py`
- **Description** :
  Centraliser la gestion des erreurs typées et orienter toute la journalisation sur `sys.stderr`.
  - Dans `src/core/exceptions.py` : `AgentSmithException` et sous-classes (`SandboxSecurityError`, `SandboxTimeoutError`, `LLMQuotaExhaustedError`, `TokenLimitExceededError`, `MaxIterationsReachedError`).
  - Dans `src/core/logger.py` : `setup_logging()` configurant `StreamHandler(sys.stderr)`.
- **Critères d'acceptation** :
  - [ ] Aucun log n'est écrit sur `stdout` (`python -m agent_mbpp ... 2>/dev/null` ne produit aucun log).
  - [ ] Une `AgentSmithException` est interceptée proprement par l'agent pour renseigner `SolutionOutput.error`.
  - [ ] `SystemExit` et `KeyboardInterrupt` ne sont jamais capturés par les blocs d'exceptions de l'agent.

---

### [S2-DEV2-02] KeyManager & TokenTracker (Anti-429 & Retries)
- **Développeur** : Dev 2
- **Fichiers** : `src/llm/key_manager.py`, `src/llm/token_tracker.py`
- **Description** :
  Découpler la rotation des clés d'API (résilience) de la métrologie et de la gestion des retries avec backoff.
  - Dans `src/llm/key_manager.py` : `class KeyManager` chargeant `{PREFIX}`, `{PREFIX}_1`, `{PREFIX}_2`... avec `get_active_key()`, `rotate_key()`, `mark_exhausted()`.
  - Dans `src/llm/token_tracker.py` : `class TokenTracker.query()` mesurant la latence, effectuant les retries avec backoff exponentiel et appelant `KeyManager.rotate_key()` sur code HTTP 429.
- **Critères d'acceptation** :
  - [ ] Simulation d'une erreur HTTP 429 → déclenchement immédiat de `rotate_key()` sans lever d'exception à l'agent.
  - [ ] Épuisement de toutes les clés → levée de `LLMQuotaExhaustedError`.
  - [ ] `StepMetrics.retries` reflète exactement le nombre de retries effectués lors du pas.

---

### [S2-DEV2-03] Extraction Multi-Formats & Plafonds MBPP
- **Développeur** : Dev 2
- **Fichiers** : `src/core/extraction.py` (enrichissement), `src/core/loop.py` (enrichissement)
- **Description** :
  Gérer l'extraction de code sur 4 formats et appliquer strictement les limites dures du benchmark MBPP.
  - Dans `src/core/extraction.py` : support XML Anthropic (`<invoke>`), JSON Hermes (`<tool_call>`), et ReAct (`Action / Action Input`), convertis en syntaxe d'appel Python.
  - Dans `src/core/loop.py` : `_enforce_hard_limits()` validant max 10 itérations, 6 000 tokens in, 1 500 out, et 120 secondes cumulées.
- **Critères d'acceptation** :
  - [ ] `test_code_extractor.py` passe avec succès sur les 4 formats.
  - [ ] Dépassement de 10 itérations → arrêt propre avec `MaxIterationsReachedError` dans `solution.json`.
  - [ ] Dépassement de 6 000 tokens in cumulés → arrêt propre avec `TokenLimitExceededError`.
  - [ ] Validation de 4/5 tâches MBPP réussie lors d'une session complète d'examen.

---

# 🔵 SPRINT 3 — Extension SWE-bench & Docker
> **Objectif du jalon** : L'agent résout de manière autonome au moins 1 bug SWE-bench dans un conteneur Docker et produit un patch git diff valide.

---

### [S3-DEV1-01] Outils Fichiers & Recherche SWE-bench
- **Développeur** : Dev 1
- **Fichiers** : `src/tools/file_tools.py`, `src/tools/search_tools.py`
- **Description** :
  Implémenter les 6 outils de navigation et d'édition de code dans le testbed (*Sections V.5.1 & V.5.2*).
  - Dans `src/tools/file_tools.py` : `class FileTools` avec `read_file` (format strict `cat -n`), `edit_file` (remplacement exact), `list_files` (glob).
  - Dans `src/tools/search_tools.py` : `class SearchTools` avec `search_code` (format grep strict `/abs/path:<line> <content>`), `search_function_or_class_definition_in_code`, `find_references`.
- **Critères d'acceptation** :
  - [ ] `read_file` affiche chaque ligne avec son numéro de ligne aligné suivi de `: `.
  - [ ] `edit_file` remplace fidèlement une sous-chaîne ou renvoie un message explicite si introuvable.
  - [ ] `search_code` produit la sortie au format `/chemin/fichier.py:<ligne> <contenu>`.
  - [ ] `test_mcp_tools.py` valide unitairement ces 6 outils.

---

### [S3-DEV1-02] Outils Exécution, Git Diff & Serveur MCP SWE-bench
- **Développeur** : Dev 1
- **Fichiers** : `src/tools/execution_tools.py`, `mcp_tools_swebench.py`, `src/mcp/client.py` (enrichissement)
- **Description** :
  Implémenter les 3 outils d'exécution/patch et le serveur MCP SWE-bench racine supportant stdio et HTTP SSE (*Section V.5.3*).
  - Dans `src/tools/execution_tools.py` : `class ExecutionTools` avec `run_tests()`, `get_patch()` (`git -c core.fileMode=false diff`), `run_command(command, workdir)`.
  - Dans `mcp_tools_swebench.py` : `class SWEBenchMCPServer` exposant les 9 outils via `TESTBED_PATH`.
  - Dans `src/mcp/client.py` : support de `connect_http(url: str)` pour transport HTTP SSE.
- **Critères d'acceptation** :
  - [ ] `get_patch()` renvoie un patch git unifié propre après une modification de fichier.
  - [ ] `run_command("pwd")` retourne le bon répertoire de travail et le code de retour 0.
  - [ ] `python mcp_tools_swebench.py` démarre sans erreur en mode stdio et répond aux appels d'outils.

---

### [S3-DEV2-01] DockerManager & Nettoyage Garanti
- **Développeur** : Dev 2
- **Fichier** : `src/tools/docker_manager.py`
- **Description** :
  Gérer le cycle de vie des conteneurs Docker pour SWE-bench avec garantie d'absence de conteneur orphelin.
  - `class DockerManager.__init__(image_name: str, instance_id: str)`.
  - `start_container() -> str` : lance le conteneur en arrière-plan et configure `TESTBED_PATH`.
  - `cleanup_container() -> None` : stoppe et supprime le conteneur.
  - Armement automatique des handlers `signal.SIGTERM`, `signal.SIGINT` et `atexit.register(cleanup_container)`.
  - `execute_in_container(command: str) -> tuple[int, str, str]`.
- **Critères d'acceptation** :
  - [ ] Le conteneur Docker de la tâche démarre et exécute des commandes.
  - [ ] Un arrêt abrupt par `Ctrl+C` ou `kill <PID>` supprime immédiatement le conteneur Docker.
  - [ ] Aucun conteneur résiduel n'apparaît dans `docker ps -a` après exécution.

---

### [S3-DEV2-02] Orchestrateur SWEBenchAgent & Plafonds Durs
- **Développeur** : Dev 2
- **Fichiers** : `src/models/tasks.py` (enrichissement), `src/agent/swebench_agent.py`, `agent_swebench.py`
- **Description** :
  Créer l'orchestrateur SWE-bench et appliquer ses limites spécifiques.
  - `class SWEBenchTaskInput` dans `src/models/tasks.py`.
  - `class SWEBenchAgent` dans `src/agent/swebench_agent.py` : pilote Docker, initialise MCP SWE-bench, exécute `AgentLoop` avec les plafonds SWE-bench (30 iters, 300k in, 10k out, 900s), et enregistre `final_answer(get_patch())`.
  - `class SWEBenchAgentApp` dans `agent_swebench.py` pour point d'entrée `python -m agent_swebench`.
- **Critères d'acceptation** :
  - [ ] `uv run python -m agent_swebench --task-file swe_task.json --output solution.json ...` s'exécute de bout en bout.
  - [ ] `SolutionOutput.solution` contient un git diff unifié non vide lors d'une résolution.
  - [ ] Dépassement de 30 itérations ou 900s → arrêt propre sans crash et statut `success: false`.

---

### [S3-DEV2-03] Prompt SWE-bench & Client Gemini
- **Développeur** : Dev 2
- **Fichiers** : `src/core/prompt.py` (enrichissement), `src/llm/gemini.py`
- **Description** :
  Spécialiser les consignes du prompt pour la navigation de grands repos et ajouter l'adaptateur Google Gemini.
  - Dans `src/core/prompt.py` : instructions de recherche chirurgicale, repérage de tests existants et obligation d'appeler `final_answer(get_patch())`.
  - Dans `src/llm/gemini.py` : `class GeminiClient(BaseLLMClient)` pour l'API Google Gemini / AI Studio.
- **Critères d'acceptation** :
  - [ ] L'agent cible correctement les fichiers de test du bug avant de modifier le code source.
  - [ ] `GeminiClient` effectue des requêtes réelles et s'intègre en fallback dans `TokenTracker`.

---

# 📊 SPRINT 4 — Benchmarks, Rapport & Soutenance (Travail Conjoint)
> **Objectif du jalon** : Rapports conformes au Chapitre V.7, documentation bilingue et validation de la grille d'examen.

---

### [S4-TEAM-01] Campagne de Benchmark (5 Modèles × 3 Tâches)
- **Développeurs** : Dev 1 + Dev 2
- **Répertoire** : `benchmark_artifacts/`
- **Description** :
  Exécuter le benchmark officiel exigé par le Chapitre V.7 sur 3 tâches SWE-bench Verified (ex: `sympy__sympy-14711`, `sympy__sympy-13480`, `pydata__xarray-4629`).
  - Comparer au moins 5 modèles sur au moins 2 providers gratuits (Groq, OpenRouter, Gemini).
  - Conserver les 15 fichiers `solution.json` dans `benchmark_artifacts/<task_id>/<model>_solution.json`.
- **Critères d'acceptation** :
  - [ ] Les 15 fichiers `solution.json` sont présents et validés sans erreur par Pydantic.
  - [ ] Au moins 2 providers distincts sont représentés dans les traces de pas (`api_url`).

---

### [S4-TEAM-02] Métriques Intermédiaires & Étude d'Ablation
- **Développeurs** : Dev 2 pilote, Dev 1 analyse
- **Fichier** : Données pour `BENCHMARK_REPORT.md`
- **Description** :
  Extraire les indicateurs d'efficacité de raisonnement et réaliser une expérience comparative d'ablation.
  - Métriques intermédiaires (au moins 2) : pas de première lecture du fichier du patch, pas de premier run de test, pas de réduction des échecs.
  - Étude d'ablation : évaluer le même modèle sur les mêmes tâches avec une modification ciblée (ex: avec vs sans l'outil `search_code`, ou prompt avec vs sans instructions d'exploration).
- **Critères d'acceptation** :
  - [ ] Tableaux des métriques intermédiaires remplis avec les données réelles issues des `solution.json`.
  - [ ] Étude d'ablation documentée avec résultats chiffrés avant/après.

---

### [S4-TEAM-03] Rédaction du BENCHMARK_REPORT.md
- **Développeur** : Dev 2 pilote
- **Fichier** : `BENCHMARK_REPORT.md` à la racine
- **Description** :
  Rédiger le rapport complet imposé par le Chapitre V.7 du sujet.
  - Setup (modèles, providers, justification du choix des tâches).
  - Tableau des résultats (Pass/Fail, itérations, tokens in/out, temps wall-clock).
  - Fiabilité provider (latence moyenne, nombre de retries).
  - Métriques intermédiaires et analyse d'ablation.
  - Conclusion justifiant le modèle retenu pour le pipeline final.
- **Critères d'acceptation** :
  - [ ] Le document contient l'ensemble des sections requises par la Section V.7.
  - [ ] Les analyses s'appuient sur les données réelles des fichiers de `benchmark_artifacts/`.

---

### [S4-TEAM-04] Rédaction du README.md (Norme 42)
- **Développeur** : Dev 1 pilote
- **Fichier** : `README.md` à la racine
- **Description** :
  Rédiger la documentation officielle en anglais respectant toutes les consignes du Chapitre VII.
  - Première ligne obligatoire en italique : *This project has been created as part of the 42 curriculum by <login1>, <login2>.*
  - Sections : Description, Instructions d'installation/lancement, Ressources & utilisation de l'IA.
  - Détail de l'architecture, de la boucle agentique, du sandbox et des outils.
- **Critères d'acceptation** :
  - [ ] Rédigé intégralement en anglais.
  - [ ] Première phrase exactement conforme aux exigences du sujet.
  - [ ] Les commandes `uv run sandbox`, `uv run python -m agent_mbpp`, et `uv run python -m agent_swebench` sont documentées et fonctionnelles.
