# Cartes Trello — Agent Smith (Roadmap 5 Semaines)

Guide de gestion de projet prêt à être importé dans Trello. Ce tableau fusionne l'approche **MBPP First** (dérisquage immédiat dès le Jour 3) avec une **roadmap sur 5 semaines**, des rôles nominatifs basés sur les compétences de **Marco** et **Steph**, et une préparation ciblée à la soutenance 42.

---

## 👥 Rôles & Compétences du Binôme

| Membre | Rôle Principal | Modules Assignés |
| :--- | :--- | :--- |
| **Marco 🛠️** | **Système & Sécurité** | Sandbox, Verrous AST/builtins/paths, Protocoles MCP, Outils système, `docker_manager.py`. |
| **Steph 🧠** | **IA & Orchestration** | Modèles Pydantic, Abstraction LLM & Quotas, Moteur `AgentLoop` ReAct, Extraction de code, Prompts, Benchmarks. |
| **Commun 🤝** | **Qualité & Examen** | Modèles de données initiaux, intégration de bout en bout, campagne de benchmark, drills live-coding 2–5 min. |

---

## 🎯 Seuils Officiels de Réussite à l'Examen
- **Sandbox** : 100 % de réussite sur `exam_sandbox.sh` (imports, builtins, réseau, chemins, mémoire).
- **MBPP** : $\ge$ 4/5 tâches réussies (*10 itérations max, 120s, 6k in, 1.5k out*).
- **SWE-bench** : $\ge$ 2/3 tâches réussies (*30 itérations max, 900s, 300k in, 10k out*).

---

# 🟡 SPRINT 1 (Semaine 1) : MVP MBPP
> **Objectif clé** : Faire tourner un premier run complet validé par la moulinette dès le Jour 3 (`uv run moulinette_eval validate mbpp`).

---

### [S1-MARCO-01] SandboxRunner Minimal & final_answer
* **Assigné** : Marco 🛠️
* **Fichier cible** : `src/sandbox/core.py`
* **Description** :
  Créer le moteur d'exécution de code Python isolé dans un sous-processus avec capture des flux et construct d'arrêt propre.
  - Définir `class FinalAnswerSignal(Exception)` avec l'attribut `answer: str`.
  - Définir `class ExecutionResult` (`stdout: str`, `stderr: str`, `exit_code: int`, `final_answer: Optional[str]`, `is_timeout: bool`, `is_truncated: bool`).
  - Implémenter `class SandboxRunner.__init__(config: SandboxConfig, tools_namespace: dict)`.
  - Implémenter `SandboxRunner.execute(code: str) -> ExecutionResult` : exécute dans un sous-processus dédié, capture `stdout`/`stderr`, injecte le callable `final_answer(str)` levant `FinalAnswerSignal`.
  - Implémenter `SandboxRunner._truncate_output(text: str, max_chars: int = 4000) -> tuple[str, bool]`.
* **Critères d'acceptation** :
  - [ ] Le code `final_answer("42")` retourne `ExecutionResult.final_answer == "42"`.
  - [ ] L'instruction `print("hello")` est bien capturée dans `ExecutionResult.stdout`.
  - [ ] Une exception Python retourne `exit_code != 0` et le traceback dans `ExecutionResult.stderr`.
  - [ ] `KeyboardInterrupt` et `SystemExit` ne sont pas interceptés silencieusement.
  - [ ] Une sortie de plus de 4000 caractères est tronquée avec la mention `[TRUNCATED]`.

---

### [S1-MARCO-02] Toolkit MBPP & Serveur MCP stdio
* **Assigné** : Marco 🛠️
* **Fichiers cibles** : `src/tools/mbpp_tools.py`, `mcp_tools_mbpp.py`
* **Description** :
  Créer l'outil d'évaluation de tests MBPP et l'exposer via le serveur MCP racine en mode stdio (*Section V.2.4*).
  - Dans `src/tools/mbpp_tools.py` : `class MBPPToolKit.run_tests(code: str, test_list: list[str]) -> str` qui exécute les assertions et renvoie `{"success": bool, "output": str}`.
  - Dans `mcp_tools_mbpp.py` : `class MBPPMCPServer` avec `register_tools()`, `run(transport="stdio")`, et `@classmethod main()`.
* **Critères d'acceptation** :
  - [ ] `MBPPToolKit().run_tests("def f(x): return x+1", ["assert f(1)==2"])` retourne `'{"success": true, "output": ""}'`.
  - [ ] Une assertion fausse retourne `'{"success": false, "output": "AssertionError..."}'`.
  - [ ] `python mcp_tools_mbpp.py` démarre en mode stdio sans crash.
  - [ ] Une requête MCP `tools/list` liste fidèlement l'outil `run_tests`.

---

### [S1-MARCO-03] Client MCP stdio & Bridge Python
* **Assigné** : Marco 🛠️
* **Fichiers cibles** : `src/mcp/client.py`, `src/mcp/bridge.py`
* **Description** :
  Connecter la sandbox au serveur MCP local et transformer l'outil distant en fonction Python directement appelable.
  - Dans `src/mcp/client.py` : `class MCPClient` avec `connect_stdio(command: str)`, `list_tools()`, `call_tool(name, args)`, `close()`.
  - Dans `src/mcp/bridge.py` : `class MCPToolBridge.__init__(client: MCPClient)` avec `create_tool_callables() -> dict[str, Callable]`.
* **Critères d'acceptation** :
  - [ ] `MCPClient.connect_stdio("python mcp_tools_mbpp.py")` initialise la session sans erreur.
  - [ ] `list_tools()` retourne le schéma de l'outil `run_tests`.
  - [ ] La fonction Python injectée par le bridge s'exécute de façon transparente à l'intérieur de `SandboxRunner`.

---

### [S1-STEPH-01] Modèles Pydantic Partagés : Config, Tasks & Metrics
* **Assigné** : Steph 🧠
* **Fichiers cibles** : `src/models/config.py`, `src/models/tasks.py`, `src/models/metrics.py`
* **Description** :
  Définir les contrats de données Pydantic stricts exigés par le sujet et la moulinette (*Section V.1.1 & V.2*).
  - Dans `src/models/config.py` : `class SandboxConfig(BaseModel)` avec `is_import_authorized(module)` (support wildcard `.*`), `is_path_authorized(path)` (`realpath`), et `from_json_file(path)`.
  - Dans `src/models/tasks.py` : `class MBPPTaskInput(BaseModel)` (`task_id`, `task_definition`, `function_definition`, `test_imports`, `test_list`).
  - Dans `src/models/metrics.py` : `class StepMetrics(BaseModel)` (tous champs requis) et `class SolutionOutput(BaseModel)` avec méthodes `record_step(step)` et `to_file(path)`.
* **Critères d'acceptation** :
  - [ ] `SandboxConfig(...).is_import_authorized("collections.abc")` retourne `True` si `"collections.*"` est configuré.
  - [ ] `SandboxConfig(...).is_import_authorized("os")` retourne `False`.
  - [ ] `MBPPTaskInput.model_validate(json_data)` parse sans erreur les fichiers de tâches de la moulinette.
  - [ ] `SolutionOutput(...).to_file("solution.json")` génère un JSON valide contenant l'intégralité des champs requis.

---

### [S1-STEPH-02] Client LLM OpenAI-Compatible & Extraction Markdown
* **Assigné** : Steph 🧠
* **Fichiers cibles** : `src/llm/base.py`, `src/llm/openai_compatible.py`, `src/core/extraction.py`
* **Description** :
  Effectuer des requêtes aux modèles gratuits (Groq, OpenRouter) et extraire le code Python généré.
  - Dans `src/llm/base.py` : `class LLMResponse(BaseModel)` et `class BaseLLMClient(ABC)`.
  - Dans `src/llm/openai_compatible.py` : `class OpenAICompatibleClient(BaseLLMClient)` avec appel HTTP POST sur `{base_url}/chat/completions`, gestion de `stop_sequences`, calcul de `latency_ms` et des tokens.
  - Dans `src/core/extraction.py` : `class CodeExtractionResult` et `class CodeExtractor` avec extraction des blocs Markdown ````python ... ````.
* **Critères d'acceptation** :
  - [ ] Une requête réelle à Groq ou OpenRouter retourne une `LLMResponse` valide.
  - [ ] `LLMResponse.input_tokens > 0` et `LLMResponse.latency_ms > 0`.
  - [ ] `CodeExtractor.extract("```python\nprint(1)\n```")` extrait le code `print(1)`.
  - [ ] L'absence de bloc de code signale explicitement `was_malformed = True`.

---

### [S1-STEPH-03] Socle Minimal : Logger stderr & Exceptions de Base
* **Assigné** : Steph 🧠
* **Fichiers cibles** : `src/core/logger.py`, `src/core/exceptions.py`
* **Description** :
  Poser dès le premier jour les bases de la journalisation et de la gestion des erreurs afin que ni l'agent ni les outils ne polluent `sys.stdout`.
  - Dans `src/core/logger.py` : fonction `setup_logging(level: str = "INFO")` configurant le module standard `logging` avec un `StreamHandler(sys.stderr)` et formatage horodaté `[%(asctime)s] [%(levelname)s] %(name)s: %(message)s`.
  - Dans `src/core/exceptions.py` :
    - `class AgentSmithException(Exception)` : classe racine pour toutes les erreurs gérées, avec méthode `to_log_message() -> str`.
    - `class LLMAPIError(AgentSmithException)` : levée lors d'un échec d'appel ou de connexion réseau avec l'API LLM.
    - `class MaxIterationsReachedError(AgentSmithException)` : levée lorsque l'agent atteint la limite d'itérations sans appeler `final_answer()`.
* **Critères d'acceptation** :
  - [ ] `setup_logging()` dirige 100 % des messages de log vers `sys.stderr`.
  - [ ] L'exécution `uv run python -m agent_mbpp ... 2>/dev/null` ne produit aucun log sur `stdout`.
  - [ ] Lever `MaxIterationsReachedError` est interceptable sans crasher le script principal.
  - [ ] `KeyboardInterrupt` et `SystemExit` ne sont jamais interceptés par `except AgentSmithException`.

---

### [S1-STEPH-04] Boucle AgentLoop MBPP & CLI agent_mbpp
* **Assigné** : Steph 🧠
* **Fichiers cibles** : `src/core/prompt.py`, `src/core/loop.py`, `src/agent/mbpp_agent.py`, `agent_mbpp.py`
* **Description** :
  Assembler le cycle *Thought → Code → Observation*, l'orchestrateur `MBPPAgent` et le point d'entrée racine.
  - Dans `src/core/prompt.py` : `class PromptManager` avec `build_system_prompt()` et `format_observation()`.
  - Dans `src/core/loop.py` : `class AgentLoop` gérant la boucle ReAct, l'appel LLM, l'extraction de code, l'exécution sandbox et la capture de `final_answer()`. Intégrer le bloc `try... except AgentSmithException as e:` qui capture les erreurs internes et peuple `SolutionOutput(success=False, error=str(e))`.
  - Dans `src/agent/mbpp_agent.py` : `class MBPPAgent` chargeant la tâche, pilotant la boucle et sauvegardant `solution.json`.
  - Dans `agent_mbpp.py` : `class MBPPAgentApp` avec `@classmethod main()` pour `uv run python -m agent_mbpp`.
* **Critères d'acceptation** :
  - [ ] `uv run python -m agent_mbpp --task-file task.json --output solution.json --model-name <name> --provider-url <url>` s'exécute sans crash.
  - [ ] L'agent résout une tâche simple (ex: addition de deux entiers) et appelle `final_answer(code)`.
  - [ ] `uv run moulinette_eval validate mbpp task.json solution.json` valide le fichier produit avec succès (**PASS**).

---

# 🟠 SPRINT 2 (Semaine 2) : Sécurité Sandbox, Quotas & 4/5 MBPP
> **Objectif clé** : Obtenir 100 % de réussite sur `exam_sandbox.sh` et passer au moins 4/5 tâches MBPP en respectant les limites dures de tokens.

---

### [S2-MARCO-01] Sécurité Sandbox Découpée (Pure Stdlib)
* **Assigné** : Marco 🛠️
* **Fichiers cibles** : `src/sandbox/security.py`, `src/sandbox/builtins_guard.py`, `src/sandbox/fs_guard.py`, `src/sandbox/limits.py`
* **Description** :
  Implémenter les verrous de sécurité sans package tiers (interdiction stricte de `RestrictedPython`).
  - Dans `src/sandbox/security.py` : `class ASTSecurityAnalyzer` rejetant via `ast.parse` les imports interdits et les attributs privés/magiques (`__subclasses__`, `__globals__`).
  - Dans `src/sandbox/builtins_guard.py` : `class BuiltinsGuard.get_safe_builtins()` filtrant `eval`, `exec`, `breakpoint`, `compile`.
  - Dans `src/sandbox/fs_guard.py` : `class FileSystemGuard.safe_open()` vérifiant `config.is_path_authorized()`.
  - Dans `src/sandbox/limits.py` : `class ResourceLimits` neutralisant `socket.socket` (`PermissionError`) et appliquant les quotas RAM (`resource.setrlimit`).
* **Critères d'acceptation** :
  - [ ] `exec("import os")` est bloqué par l'analyseur AST.
  - [ ] `exec("open('/etc/passwd')")` lève `SandboxSecurityError`.
  - [ ] `exec("import socket; socket.socket()")` lève `PermissionError`.
  - [ ] `exec("eval('1+1')")` lève `NameError`.
  - [ ] Tous les tests de sécurité de `exam_sandbox.sh` passent avec succès.

---

### [S2-MARCO-02] Timeout Process & Manuel Dynamique MCP
* **Assigné** : Marco 🛠️
* **Fichiers cibles** : `src/sandbox/core.py` (enrichissement), `src/mcp/dynamic_manual.py`
* **Description** :
  Interrompre de force les boucles infinies après 30s et synthétiser dynamiquement la doc des outils pour le prompt.
  - Dans `src/sandbox/core.py` : terminer le sous-processus via `terminate()` / `kill()` à $t \ge 30$s (`max_execution_time_seconds`). Positionner `ExecutionResult.is_timeout = True`.
  - Dans `src/mcp/dynamic_manual.py` : `class DynamicManualGenerator.generate(tools: list[MCPToolDefinition]) -> str` produisant la documentation Markdown à injecter dans le prompt système du LLM.
* **Critères d'acceptation** :
  - [ ] Un code `while True: pass` est tué en $\le 32$ secondes sans bloquer l'appelant.
  - [ ] `ExecutionResult.is_timeout == True` lors du dépassement.
  - [ ] Le manuel généré liste fidèlement noms, signatures et descriptions des outils MCP connectés.

---

### [S2-MARCO-03] REPL CLI Sandbox (uv run sandbox)
* **Assigné** : Marco 🛠️
* **Fichiers cibles** : `src/sandbox/cli.py`, `pyproject.toml`
* **Description** :
  Fournir l'interface de test interactif en ligne de commande conforme à la Section V.2.1.
  - Dans `src/sandbox/cli.py` : `class SandboxCLIApp` avec parsing arguments (`config.json`, `--mcp-stdio`, `--mcp-server`), invite `>>> `, exécution isolée, affichage résultat, sortie sur `exit` ou `Ctrl+D` (EOF).
  - Déclarer le script console dans `pyproject.toml` : `[project.scripts] sandbox = "src.sandbox.cli:SandboxCLIApp.main"`.
* **Critères d'acceptation** :
  - [ ] `uv run sandbox` ouvre l'invite de commande interactive `>>> `.
  - [ ] `uv run sandbox sandbox_template.json --mcp-stdio "python mcp_tools_mbpp.py"` connecte les outils MBPP.
  - [ ] Taper `Ctrl+D` ou `exit` quitte proprement le programme avec le code de sortie 0.

---

### [S2-STEPH-01] Durcissement Exceptions Sandbox/Quotas & Logs Fichiers
* **Assigné** : Steph 🧠
* **Fichiers cibles** : `src/core/exceptions.py`, `src/core/logger.py` (enrichissements)
* **Description** :
  Compléter la hiérarchie d'erreurs avec les exceptions spécialisées pour la sécurité sandbox et les quotas, et supporter la journalisation dans les fichiers d'évaluation du sujet (*Section VI.5*).
  - Dans `src/core/exceptions.py` :
    - `class SandboxSecurityError(AgentSmithException)` : levée lors d'une tentative d'intrusion détectée par les verrous de Marco.
    - `class SandboxTimeoutError(AgentSmithException)` : levée sur exécution dépassant 30 secondes.
    - `class SandboxMemoryError(AgentSmithException)` : levée lors d'un dépassement de mémoire RAM.
    - `class LLMQuotaExhaustedError(AgentSmithException)` : levée par `KeyManager` quand toutes les clés sont en erreur 429.
    - `class TokenLimitExceededError(AgentSmithException)` : levée lors du dépassement des plafonds hard de tokens.
  - Dans `src/core/logger.py` : enrichir `setup_logging(level, log_file: Optional[Path])` pour supporter un `FileHandler` écrivant dans `./evaluations/.../stderr.log`.
* **Critères d'acceptation** :
  - [ ] Les verrous de Marco lèvent `SandboxSecurityError` et sont interceptés sans crash par `AgentLoop`.
  - [ ] L'épuisement de toutes les clés d'API lève `LLMQuotaExhaustedError` et peuple `SolutionOutput.error`.
  - [ ] Si `log_file` est spécifié, les logs sont écrits simultanément dans le fichier et sur `sys.stderr`.

---

### [S2-STEPH-02] KeyManager & TokenTracker (Anti-429 & Retries)
* **Assigné** : Steph 🧠
* **Fichiers cibles** : `src/llm/key_manager.py`, `src/llm/token_tracker.py`
* **Description** :
  Gérer la rotation de clés sur rate-limit (HTTP 429) et suivre précisément la métrologie des appels API.
  - Dans `src/llm/key_manager.py` : `class KeyManager` chargeant le pool de clés (`{PREFIX}`, `{PREFIX}_1`, `{PREFIX}_2`...), avec `get_active_key()`, `rotate_key()`, et `mark_exhausted()`.
  - Dans `src/llm/token_tracker.py` : `class TokenTracker.query()` calculant la latence wall-clock, effectuant les retries avec backoff exponentiel et déclenchant la rotation sur HTTP 429.
* **Critères d'acceptation** :
  - [ ] Une erreur HTTP 429 déclenche la rotation immédiate de clé sans lever d'exception vers l'agent.
  - [ ] L'épuisement de toutes les clés lève proprement `LLMQuotaExhaustedError`.
  - [ ] `StepMetrics.retries` reflète exactement le nombre de retries effectués.

---

### [S2-STEPH-03] Extraction Multi-Formats & Validation 4/5 MBPP
* **Assigné** : Steph 🧠
* **Fichiers cibles** : `src/core/extraction.py` (enrichissement), `src/core/loop.py` (enrichissement)
* **Description** :
  Prendre en charge les formats alternatifs des LLMs et valider la conformité aux plafonds stricts MBPP.
  - Dans `src/core/extraction.py` : conversion en code Python des formats XML Anthropic (`<invoke>`), JSON Hermes (`<tool_call>`), et ReAct (`Action / Action Input`).
  - Dans `src/core/loop.py` : `_enforce_hard_limits()` validant max 10 itérations, 6 000 tokens in, 1 500 out, et 120 secondes globales.
* **Critères d'acceptation** :
  - [ ] `test_code_extractor.py` passe avec succès sur les 4 formats de sortie.
  - [ ] Dépassement de 10 itérations $\rightarrow$ arrêt propre avec `MaxIterationsReachedError` dans `solution.json`.
  - [ ] Dépassement de 6 000 tokens in $\rightarrow$ arrêt propre avec `TokenLimitExceededError`.
  - [ ] L'agent résout avec succès au moins 4/5 tâches MBPP lors d'un test complet avec la moulinette.

---

# 🔵 SPRINT 3 (Semaines 3 & 4) : SWE-bench & Docker
> **Objectif clé** : L'agent résout au moins 2 bugs sur 3 dans un conteneur Docker SWE-bench et produit un patch `git diff` valide.

---

### [S3-MARCO-01] Outils Fichiers & Recherche de Code SWE-bench
* **Assigné** : Marco 🛠️
* **Fichiers cibles** : `src/tools/file_tools.py`, `src/tools/search_tools.py`
* **Description** :
  Implémenter les 6 outils obligatoires d'exploration et d'édition de code dans le repo (*Sections V.5.1 & V.5.2*).
  - Dans `src/tools/file_tools.py` : `class FileTools` avec `read_file` (format strict `cat -n`), `edit_file` (remplacement exact), `list_files` (glob).
  - Dans `src/tools/search_tools.py` : `class SearchTools` avec `search_code` (format grep strict `/abs/path:<line> <content>`), `search_function_or_class_definition_in_code`, `find_references`.
* **Critères d'acceptation** :
  - [ ] `read_file` affiche chaque ligne avec son numéro aligné suivi de `: `.
  - [ ] `edit_file` remplace fidèlement une chaîne ou retourne un message d'erreur si introuvable.
  - [ ] `search_code` produit la sortie au format `/chemin/fichier.py:<ligne> <contenu>`.
  - [ ] `test_mcp_tools.py` valide unitairement ces 6 outils.

---

### [S3-MARCO-02] Outils Exécution, Git Diff & Serveur MCP SWE-bench
* **Assigné** : Marco 🛠️
* **Fichiers cibles** : `src/tools/execution_tools.py`, `mcp_tools_swebench.py`, `src/mcp/client.py` (enrichissement)
* **Description** :
  Implémenter les 3 outils d'exécution/patch et le serveur MCP SWE-bench supportant stdio et HTTP SSE (*Section V.5.3*).
  - Dans `src/tools/execution_tools.py` : `class ExecutionTools` avec `run_tests()` (dans `TESTBED_PATH`), `get_patch()` (`git -c core.fileMode=false diff`), `run_command(command, workdir)`.
  - Dans `mcp_tools_swebench.py` : `class SWEBenchMCPServer` exposant les 9 outils via `TESTBED_PATH`.
  - Dans `src/mcp/client.py` : implémenter `connect_http(url: str)` pour le streaming HTTP SSE.
* **Critères d'acceptation** :
  - [ ] `get_patch()` renvoie un patch git unifié propre après une modification de fichier.
  - [ ] `run_command("pwd")` retourne le bon répertoire de travail et le code de retour 0.
  - [ ] `python mcp_tools_swebench.py` démarre sans erreur en mode stdio et répond aux requêtes MCP.

---

### [S3-MARCO-03] DockerManager & Nettoyage Garanti des Conteneurs
* **Assigné** : Marco 🛠️
* **Fichier cible** : `src/tools/docker_manager.py`
* **Description** :
  Gérer l'orchestration des conteneurs Docker pour SWE-bench avec garantie d'absence de conteneur orphelin (*Section V.4*).
  - `class DockerManager.__init__(image_name: str, instance_id: str)`.
  - `start_container() -> str` : lance le conteneur en arrière-plan et configure `TESTBED_PATH`.
  - `cleanup_container() -> None` : stoppe et supprime le conteneur.
  - Armer les handlers `signal.SIGTERM`, `signal.SIGINT` et `atexit.register(cleanup_container)`.
  - `execute_in_container(command: str) -> tuple[int, str, str]`.
* **Critères d'acceptation** :
  - [ ] Le conteneur Docker de la tâche démarre et exécute des commandes via `execute_in_container()`.
  - [ ] Une interruption par `Ctrl+C` ou signal POSIX supprime immédiatement le conteneur.
  - [ ] Aucun conteneur résiduel n'apparaît dans `docker ps -a` après exécution.

---

### [S3-STEPH-01] Orchestrateur SWEBenchAgent & Plafonds Durs
* **Assigné** : Steph 🧠
* **Fichiers cibles** : `src/models/tasks.py` (enrichissement), `src/agent/swebench_agent.py`, `agent_swebench.py`
* **Description** :
  Créer l'orchestrateur SWE-bench et appliquer ses limites spécifiques dans la boucle agent.
  - `class SWEBenchTaskInput` dans `src/models/tasks.py` (`instance_id`, `problem_statement`, `docker_image`, `eval_script`, `hints_text`, `repo`).
  - Dans `src/agent/swebench_agent.py` : `class SWEBenchAgent` pilotant `DockerManager`, initialisant MCP SWE-bench, exécutant `AgentLoop` avec les plafonds SWE-bench (30 iters, 300k in, 10k out, 900s), et appelant `final_answer(get_patch())`.
  - Dans `agent_swebench.py` : `class SWEBenchAgentApp` pour l'entrée CLI `python -m agent_swebench`.
* **Critères d'acceptation** :
  - [ ] `uv run python -m agent_swebench --task-file swe_task.json --output solution.json ...` s'exécute de bout en bout.
  - [ ] `SolutionOutput.solution` contient un git diff unifié non vide lors d'une résolution.
  - [ ] Dépassement de 30 itérations ou 900s $\rightarrow$ arrêt propre sans crash et statut `success: false`.

---

### [S3-STEPH-02] Spécialisation Prompt SWE-bench & Client Gemini
* **Assigné** : Steph 🧠
* **Fichiers cibles** : `src/core/prompt.py` (enrichissement), `src/llm/gemini.py`
* **Description** :
  Spécialiser les consignes du prompt pour la navigation de grands dépôts et ajouter l'adaptateur Google Gemini.
  - Dans `src/core/prompt.py` : consignes méthodologiques (rechercher le bug, localiser les tests existants, modifier de façon chirurgicale, soumettre avec `final_answer(get_patch())`).
  - Dans `src/llm/gemini.py` : `class GeminiClient(BaseLLMClient)` pour l'API Google Gemini / AI Studio.
* **Critères d'acceptation** :
  - [ ] L'agent cible correctement les fichiers de test du bug avant de modifier le code source.
  - [ ] `GeminiClient` effectue des requêtes réelles et s'intègre en fallback dans `TokenTracker`.
  - [ ] L'agent résout au moins 2 tâches sur 3 recommandées (`sympy__sympy-14711`, `sympy__sympy-13480`, `pydata__xarray-4629`).

---

# 📊 SPRINT 4 (Semaine 5) : Benchmarks, Documentation & Soutenance
> **Objectif clé** : Finaliser le benchmark 5 modèles, rédiger les livrables obligatoires et maîtriser le live-coding de soutenance.

---

### [S4-TEAM-01] Campagne de Benchmark (5 Modèles × 3 Tâches)
* **Assigné** : Marco 🛠️ & Steph 🧠
* **Répertoire cible** : `benchmark_artifacts/`
* **Description** :
  Exécuter le benchmark officiel exigé par le Chapitre V.7 sur 3 tâches SWE-bench Verified.
  - Comparer au moins 5 modèles sur au moins 2 providers gratuits (Groq, OpenRouter, Gemini).
  - Conserver les 15 fichiers `solution.json` dans `benchmark_artifacts/<task_id>/<model>_solution.json`.
* **Critères d'acceptation** :
  - [ ] Les 15 fichiers `solution.json` sont présents et validés sans erreur par Pydantic.
  - [ ] Au moins 2 providers distincts sont représentés dans les traces de pas (`api_url`).

---

### [S4-TEAM-02] Métriques Intermédiaires & Étude d'Ablation
* **Assigné** : Steph 🧠 (pilote), Marco 🛠️ (analyse)
* **Fichier cible** : Données pour `BENCHMARK_REPORT.md`
* **Description** :
  Extraire les indicateurs d'efficacité de raisonnement et réaliser une expérience comparative d'ablation.
  - Métriques intermédiaires : pas de première lecture du fichier du patch, pas de premier test, pas de diminution des échecs.
  - Étude d'ablation : évaluer le même modèle sur les mêmes tâches avec une modification ciblée (ex: avec vs sans l'outil `search_code`, ou prompt avec vs sans consignes d'exploration).
* **Critères d'acceptation** :
  - [ ] Tableaux des métriques intermédiaires remplis avec les données réelles issues des `solution.json`.
  - [ ] Étude d'ablation documentée avec résultats chiffrés avant/après.

---

### [S4-TEAM-03] Rédaction du BENCHMARK_REPORT.md
* **Assigné** : Steph 🧠
* **Fichier cible** : `BENCHMARK_REPORT.md` à la racine
* **Description** :
  Rédiger le rapport comparatif complet conformément au Chapitre V.7 du sujet.
  - Setup (modèles, providers, justification du choix des tâches).
  - Tableau des résultats (Pass/Fail, itérations, tokens in/out, temps wall-clock).
  - Fiabilité provider (latence moyenne, nombre de retries).
  - Métriques intermédiaires et analyse d'ablation.
  - Conclusion argumentée sur le modèle sélectionné.
* **Critères d'acceptation** :
  - [ ] Le document contient l'intégralité des sections requises par la Section V.7.
  - [ ] Les analyses s'appuient sur les données réelles des fichiers de `benchmark_artifacts/`.

---

### [S4-TEAM-04] Rédaction du README.md (Norme 42)
* **Assigné** : Marco 🛠️
* **Fichier cible** : `README.md` à la racine
* **Description** :
  Rédiger la documentation officielle en anglais respectant les exigences du Chapitre VII.
  - Première ligne en italique : *This project has been created as part of the 42 curriculum by <login1>, <login2>.*
  - Sections obligatoires : Description, Instructions d'installation/lancement, Ressources & utilisation de l'IA.
  - Détail de l'architecture, de la boucle agentique, du sandbox et des outils.
* **Critères d'acceptation** :
  - [ ] Rédigé intégralement en anglais.
  - [ ] Première phrase exactement conforme aux exigences du sujet.
  - [ ] Les commandes `uv run sandbox`, `uv run python -m agent_mbpp`, et `uv run python -m agent_swebench` sont documentées.

---

### [S4-TEAM-05] Audit de Sécurité Pré-Rendu & Nettoyage
* **Assigné** : Marco 🛠️
* **Description** :
  Vérifier l'absence totale de fuites de secrets ou de résidus polluant le dépôt Git (*Section VI.3*).
  - Exécuter `git log -S "sk-"` et scanner les commits pour vérifier qu'aucune clé API réelle n'est présente dans l'historique.
  - Vérifier que `.env` est bien dans `.gitignore` et que seul `.env.example` est committé.
  - Nettoyer les fichiers de cache (`__pycache__`, `.pytest_cache`), conteneurs orphelins et sorties temporaires.
* **Critères d'acceptation** :
  - [ ] Zéro clé API présente dans l'historique Git (`git log`).
  - [ ] Pas d'images Docker, de conteneurs résiduels ou de fichiers temporaires dans le repository.

---

### [S4-TEAM-06] Drill Intensif Live-Coding Soutenance
* **Assigné** : Marco 🛠️ & Steph 🧠 (Ensemble)
* **Description** :
  S'entraîner à l'épreuve éliminatoire de live-coding en 2 à 5 minutes (*Section VI.4.1*).
  - Marco donne des exercices à Steph (ex: ajouter un paramètre à `read_file`, modifier un code de retour, interdire un nouvel import).
  - Steph donne des exercices à Marco (ex: modifier la stop sequence, changer la politique de retry, modifier le prompt système).
  - Chronométrer chaque exercice pour être capable de modifier et tester n'importe quelle partie du projet en moins de 3 minutes.
* **Critères d'acceptation** :
  - [ ] Les deux membres sont capables de localiser et modifier n'importe quel composant en moins de 3 minutes.
  - [ ] Les tests associés sont relancés et passent immédiatement après la modification.
