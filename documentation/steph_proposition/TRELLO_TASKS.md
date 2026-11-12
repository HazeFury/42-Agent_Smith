# Cartes Trello — Agent Smith (Format Prêt à l'Emploi)

Format de chaque carte :
- **Titre** : Court, actionnable, copié tel quel dans Trello.
- **Description** : Ce qu'il faut coder, dans quel fichier, avec quelles classes/méthodes.
- **Critères d'acceptation** : Liste de vérifications binaires (✅ ou ❌), testables immédiatement.

---

# 🟡 SPRINT 1 — MVP MBPP
> Fin de sprint : `uv run python -m agent_mbpp` résout une tâche MBPP et produit un `solution.json` valide.

---

## [S1-DEV1-01] SandboxRunner : Exécution Isolée & final_answer

**Label** : `Dev 1` · `Sprint 1` · `Sandbox`

**Description**
Implémenter l'exécuteur de code Python en sous-processus isolé.
Fichier cible : `src/sandbox/runner.py`

Classes à créer :

**`FinalAnswerSignal(Exception)`**
- Attribut `answer: str`
- Levée depuis le callable injecté `final_answer()`

**`ExecutionResult`**
- Champs : `stdout: str`, `stderr: str`, `exit_code: int`, `final_answer: Optional[str]`, `is_timeout: bool`, `is_truncated: bool`

**`SandboxRunner`**
- `__init__(config: SandboxConfig, tools_namespace: dict)` : stocke la config et le namespace des outils
- `execute(code: str) -> ExecutionResult` : exécute dans un sous-processus séparé, redirige stdout/stderr, injecte `final_answer()` dans les globals
- `_truncate_output(text: str, max_chars: int = 4000) -> tuple[str, bool]` : tronque avec note explicite si dépassement

**Critères d'acceptation**
- [ ] Le code `final_answer("bonjour")` retourne `ExecutionResult.final_answer == "bonjour"`
- [ ] La sortie `print("hello")` est capturée dans `ExecutionResult.stdout`
- [ ] Une exception Python dans le code retourne `ExecutionResult.exit_code != 0` et le traceback dans `stderr`
- [ ] `KeyboardInterrupt` et `SystemExit` ne sont pas interceptés silencieusement
- [ ] Une sortie de plus de 4000 caractères est tronquée avec la mention `[TRUNCATED]`

---

## [S1-DEV1-02] MBPPToolKit & Serveur MCP stdio

**Label** : `Dev 1` · `Sprint 1` · `MCP`

**Description**
Coder l'unique outil MBPP et l'exposer via un serveur MCP en mode stdio.
Fichiers cibles : `src/tools/mbpp.py`, `mcp_tools_mbpp.py`

**`MBPPToolKit`** dans `src/tools/mbpp.py`
- `__init__()`
- `run_tests(code: str, test_list: list[str]) -> str` : exécute les assertions Python et retourne `'{"success": true/false, "output": "..."}'`

**`MBPPMCPServer`** dans `mcp_tools_mbpp.py`
- `__init__(toolkit: Optional[MBPPToolKit] = None)`
- `register_tools() -> None` : enregistre `run_tests` sur le serveur MCP
- `run(transport: str = "stdio") -> None` : démarre l'écoute
- `@classmethod main() -> None` : parse les arguments et lance le serveur

**Critères d'acceptation**
- [ ] `MBPPToolKit().run_tests("def f(x): return x+1", ["assert f(1)==2"])` retourne `'{"success": true, "output": ""}'`
- [ ] `MBPPToolKit().run_tests("def f(x): return x", ["assert f(1)==2"])` retourne `'{"success": false, "output": "AssertionError..."}'`
- [ ] `python mcp_tools_mbpp.py` démarre sans erreur
- [ ] Le serveur répond correctement à une requête `tools/list` via le protocole MCP

---

## [S1-DEV1-03] MCPClient stdio & Injection dans Sandbox

**Label** : `Dev 1` · `Sprint 1` · `MCP`

**Description**
Connecter la sandbox au serveur MCP MBPP et exposer ses outils comme fonctions Python.
Fichiers cibles : `src/mcp/client.py`, `src/mcp/tools.py`

**`MCPToolDefinition(BaseModel)`** dans `src/mcp/client.py`
- Champs : `name: str`, `description: str`, `parameters: dict`

**`MCPClient`** dans `src/mcp/client.py`
- `__init__()`
- `async connect_stdio(command: str) -> None` : lance le sous-processus et établit la session MCP
- `async list_tools() -> list[MCPToolDefinition]`
- `async call_tool(name: str, arguments: dict) -> Any`
- `async close() -> None`

**`MCPToolManager`** dans `src/mcp/tools.py`
- `__init__(client: MCPClient)`
- `async create_tool_callables() -> dict[str, Callable]` : génère des fonctions Python appelables depuis la sandbox, chacune faisant un `await client.call_tool(...)` sous le capot

**Critères d'acceptation**
- [ ] Le client se connecte au serveur MCP MBPP en stdio sans erreur
- [ ] `list_tools()` retourne la définition de l'outil `run_tests`
- [ ] `call_tool("run_tests", {"code": "...", "test_list": [...]})` retourne le résultat JSON attendu
- [ ] La fonction Python générée `run_tests(code, test_list)` fonctionne dans le namespace de la sandbox

---

## [S1-DEV2-01] Modèles Pydantic : Tâches, Métriques & Config Sandbox

**Label** : `Dev 2` · `Sprint 1` · `Modèles`

**Description**
Définir tous les modèles de données validés par la moulinette.
Fichiers cibles : `src/models/tasks.py`, `src/models/metrics.py`, `src/models/sandbox.py`

**`MBPPTaskInput(BaseModel)`** dans `src/models/tasks.py`
- Champs : `task_id: int`, `task_definition: str`, `function_definition: str`, `test_imports: list[str]`, `test_list: list[str]`

**`StepMetrics(BaseModel)`** dans `src/models/metrics.py`
- Champs obligatoires (Section V.1.1) : `step`, `input_tokens`, `output_tokens`, `request_time_ms`, `timestamp`, `api_url`, `model_name`, `llm_output`, `sandbox_input`, `sandbox_output`, `retries`

**`SolutionOutput(BaseModel)`** dans `src/models/metrics.py`
- Champs : `task_id`, `benchmark`, `success`, `solution`, `iterations`, `total_requests`, `total_input_tokens`, `total_output_tokens`, `total_time_seconds`, `steps`, `system_prompt`, `error`, `timestamp`
- `record_step(step: StepMetrics) -> None` : incrémente `total_input_tokens`, `total_output_tokens`, `total_requests`
- `to_file(path: Path) -> None` : sauvegarde en JSON indenté

**`SandboxConfig(BaseModel)`** dans `src/models/sandbox.py`
- Champs : `authorized_imports: list[str]`, `allowed_directories: list[str]`, `max_execution_time_seconds: int = 30`, `max_memory_mb: int = 512`
- `is_import_authorized(module_name: str) -> bool` : accepte `math` si `"math"` ou `"math.*"` est dans la liste
- `is_path_authorized(path: str | Path) -> bool` : compare le chemin canonique `os.path.realpath(path)` aux répertoires autorisés
- `@classmethod from_json_file(path: Path) -> "SandboxConfig"`

**Critères d'acceptation**
- [ ] `SandboxConfig(...).is_import_authorized("collections.abc")` retourne `True` si `"collections.*"` est dans la liste
- [ ] `SandboxConfig(...).is_import_authorized("os")` retourne `False`
- [ ] `SolutionOutput(...).to_file("solution.json")` crée un fichier JSON valide contenant tous les champs requis
- [ ] `MBPPTaskInput.model_validate(json.loads(task_file_content))` parse sans erreur le fichier de tâche de la moulinette

---

## [S1-DEV2-02] Client LLM OpenAI-Compatible & Extraction Markdown

**Label** : `Dev 2` · `Sprint 1` · `LLM`

**Description**
Appeler un premier modèle LLM et extraire le code Python de sa réponse.
Fichiers cibles : `src/llm/base.py`, `src/llm/openai_compatible.py`, `src/core/extraction.py`

**`LLMResponse(BaseModel)`** dans `src/llm/base.py`
- Champs : `text: str`, `input_tokens: int`, `output_tokens: int`, `latency_ms: float`, `model_name: str`, `api_url: str`

**`BaseLLMClient(ABC)`** dans `src/llm/base.py`
- `__init__(model_name: str, base_url: str, api_key: str)`
- `@abstractmethod async generate(messages: list[dict], stop_sequences: Optional[list[str]] = None) -> LLMResponse`

**`OpenAICompatibleClient(BaseLLMClient)`** dans `src/llm/openai_compatible.py`
- `async generate(...)` : POST sur `{base_url}/chat/completions`, mesure `latency_ms`, extrait `usage.prompt_tokens` et `usage.completion_tokens`

**`CodeExtractionResult(BaseModel)`** dans `src/core/extraction.py`
- Champs : `code: str`, `was_malformed: bool`, `format_detected: str`, `explanation: str`

**`CodeExtractor`** dans `src/core/extraction.py`
- `extract(response_text: str) -> CodeExtractionResult`
- `_extract_python_block(text: str) -> Optional[CodeExtractionResult]` : blocs ` ```python ... ``` ` ou ` ``` ... <end_code> `

**Critères d'acceptation**
- [ ] `OpenAICompatibleClient` fait une requête réelle à Groq ou OpenRouter et retourne une `LLMResponse`
- [ ] `LLMResponse.input_tokens > 0` et `LLMResponse.latency_ms > 0`
- [ ] `CodeExtractor().extract("```python\nprint('hello')\n```")` retourne un `CodeExtractionResult.code == "print('hello')"`
- [ ] Un texte sans bloc de code retourne `was_malformed == True`

---

## [S1-DEV2-03] AgentLoop MBPP & CLI agent_mbpp

**Label** : `Dev 2` · `Sprint 1` · `Agent`

**Description**
Assembler la boucle de raisonnement *Thought → Code → Observation* et créer le script d'évaluation.
Fichiers cibles : `src/core/prompt.py`, `src/core/loop.py`, `agent_mbpp.py`

**`PromptManager`** dans `src/core/prompt.py`
- `__init__(base_instructions: str)`
- `build_system_prompt(tool_manual: str) -> str` : assemble les instructions + manuel d'outils + règle `final_answer`
- `format_observation(stdout: str, stderr: str, is_timeout: bool = False, truncated: bool = False) -> str`

**`AgentLoop`** dans `src/core/loop.py`
- `__init__(llm_router, sandbox_runner, prompt_manager, extractor, max_iterations, max_input_tokens, max_output_tokens, timeout_seconds)`
- `run(task_id: str, benchmark: str, user_prompt: str, tool_manual: str) -> SolutionOutput`
- `_enforce_hard_limits(iteration, cumulative_in, cumulative_out, elapsed) -> None` : lève une exception si dépassement

**`MBPPAgentApp`** dans `agent_mbpp.py`
- `__init__(args=None)` : parse `--task-file`, `--output`, `--model-name`, `--provider-url`, `--max-iterations`
- `load_task() -> MBPPTaskInput`
- `bootstrap_environment() -> tuple[SandboxRunner, LLMRouter]`
- `execute() -> SolutionOutput`
- `save_solution(solution: SolutionOutput) -> None`
- `@classmethod main() -> None`

**Critères d'acceptation**
- [ ] `uv run python -m agent_mbpp --task-file task.json --output solution.json --model-name <model> --provider-url <url>` s'exécute sans erreur
- [ ] Le `solution.json` produit contient `success`, `steps`, `total_input_tokens`, `system_prompt`
- [ ] L'agent s'arrête dès que `final_answer()` est appelée (pas forcément à l'itération max)
- [ ] En cas d'erreur LLM, le script ne crashe pas et écrit `solution.json` avec `success: false` et le message d'erreur

---

# 🟠 SPRINT 2 — Sécurité, Robustesse & 4/5 MBPP
> Fin de sprint : `exam_sandbox.sh` passe à 100 %. L'agent tient 4/5 sur MBPP malgré les plafonds et le rate-limiting.

---

## [S2-DEV1-01] SecurityEnforcer : Verrous Sandbox Pure Stdlib

**Label** : `Dev 1` · `Sprint 2` · `Sécurité`

**Description**
Neutraliser tous les vecteurs d'attaque dans la sandbox sans aucune dépendance externe.
Fichier cible : `src/sandbox/security.py`

**`SecurityEnforcer`**
- `__init__(config: SandboxConfig)`
- `install_import_hook() -> None` : insère un finder custom dans `sys.meta_path` qui appelle `config.is_import_authorized()` et lève `ImportError` si refus
- `sanitize_builtins() -> dict` : construit un dict de builtins sans `eval`, `exec`, `breakpoint`, `compile`, `__import__`; surcharge `open` pour vérifier `config.is_path_authorized()`
- `disable_network() -> None` : remplace `socket.socket.__init__` par une méthode levant `PermissionError("Network access is disabled")`
- `set_resource_limits() -> None` : appelle `resource.setrlimit(resource.RLIMIT_AS, (max_bytes, max_bytes))`
- `apply_all_guards() -> dict` : appelle les 4 méthodes ci-dessus et retourne le namespace assaini prêt à être injecté dans `SandboxRunner`

**Critères d'acceptation**
- [ ] `exec("import os")` dans le namespace assaini lève `ImportError`
- [ ] `exec("import math")` dans le namespace assaini réussit si `math` est dans l'allowlist
- [ ] `exec("open('/etc/passwd')")` lève une erreur si `/etc` n'est pas dans `allowed_directories`
- [ ] `exec("import socket; socket.socket()")` lève `PermissionError`
- [ ] `exec("eval('1+1')")` lève `NameError` (eval supprimé des builtins)
- [ ] Tous les tests de `exam_sandbox.sh` passent

---

## [S2-DEV1-02] Timeout 30s & Troncature des Sorties

**Label** : `Dev 1` · `Sprint 2` · `Sandbox`

**Description**
Terminer de force le code bouclant à l'infini et éviter de saturer le contexte LLM avec de longues sorties.
Fichier cible : `src/sandbox/runner.py` (enrichissement)

Modifier `SandboxRunner.execute()` pour :
- Lancer le code dans un `multiprocessing.Process` avec `timeout=config.max_execution_time_seconds`
- Appeler `process.terminate()` puis `process.kill()` si le processus ne s'arrête pas
- Renseigner `ExecutionResult.is_timeout = True` en cas de dépassement
- Appeler `_truncate_output()` sur `stdout` et `stderr` avant de retourner le résultat

**Critères d'acceptation**
- [ ] `runner.execute("while True: pass")` retourne après ≤ 32 secondes
- [ ] `ExecutionResult.is_timeout == True` pour le code bouclant
- [ ] Un code qui génère 10 000 lignes de sortie retourne `is_truncated == True` et `stdout` tronqué à ~4000 caractères avec la mention `[OUTPUT TRUNCATED]` à la fin
- [ ] Un code qui s'arrête normalement en 1 seconde retourne `is_timeout == False`

---

## [S2-DEV1-03] CLI Interactif `uv run sandbox`

**Label** : `Dev 1` · `Sprint 2` · `Sandbox`

**Description**
Fournir le REPL interactif de test manuel de la sandbox (Section V.2.1).
Fichiers cibles : `src/sandbox/cli.py`, `pyproject.toml`

**`SandboxCLIApp`** dans `src/sandbox/cli.py`
- `__init__(argv: Optional[list[str]] = None)` : parse positional `config.json` optionnel, `--mcp-stdio <command>`, `--mcp-server <url>`
- `setup_session() -> None` : charge `SandboxConfig`, se connecte au serveur MCP si spécifié, initialise `SandboxRunner`
- `start_repl() -> None` : boucle `while True` → affiche `>>> ` → lit l'entrée → `execute()` → affiche résultat; quitte sur `exit` ou `EOFError`
- `@classmethod main() -> None`

Dans `pyproject.toml` :
```toml
[project.scripts]
sandbox = "src.sandbox.cli:SandboxCLIApp.main"
```

**Critères d'acceptation**
- [ ] `uv run sandbox` ouvre une invite `>>> ` interactive
- [ ] `uv run sandbox sandbox_template.json` charge la configuration sans erreur
- [ ] `uv run sandbox sandbox_template.json --mcp-stdio "python mcp_tools_mbpp.py"` connecte le serveur MCP et expose `run_tests` dans le REPL
- [ ] Taper `exit` ou `Ctrl+D` ferme proprement le CLI

---

## [S2-DEV2-01] Exceptions Typées & Logging stderr

**Label** : `Dev 2` · `Sprint 2` · `Robustesse`

**Description**
Garantir qu'aucune erreur interne ne crashe l'agent et que les logs ne polluent jamais `stdout`.
Fichiers cibles : `src/core/exceptions.py`, `src/core/logger.py`

**Hiérarchie dans `src/core/exceptions.py`**
- `AgentSmithException(Exception)` : méthode `to_log_message() -> str`
- `SandboxSecurityError(AgentSmithException)` : violation import, path, réseau
- `SandboxTimeoutError(AgentSmithException)` : dépassement des 30s
- `SandboxMemoryError(AgentSmithException)` : dépassement RAM
- `MCPCommunicationError(AgentSmithException)` : rupture de connexion MCP
- `LLMQuotaExhaustedError(AgentSmithException)` : toutes les clés en 429
- `TokenLimitExceededError(AgentSmithException)` : plafond de tokens cumulés
- `MaxIterationsReachedError(AgentSmithException)` : max iters sans `final_answer`

**Dans `src/core/logger.py`**
- `setup_logging(level: str = "INFO", log_file: Optional[Path] = None) -> None` : configure `logging.basicConfig` avec `stream=sys.stderr` et format `[%(asctime)s] [%(levelname)s] %(name)s: %(message)s`
- Tous les modules utilisent ensuite `import logging; logger = logging.getLogger(__name__)`

**Critères d'acceptation**
- [ ] Lever `LLMQuotaExhaustedError` depuis la boucle agent produit un `SolutionOutput` avec `success: false` et `error: "..."` sans crash
- [ ] Aucun log n'apparaît sur `stdout` (vérifiable avec `uv run python -m agent_mbpp ... 2>/dev/null | grep -c "."`)
- [ ] `SystemExit` et `KeyboardInterrupt` ne sont pas interceptés par les `except AgentSmithException`

---

## [S2-DEV2-02] TokenRotator & LLMRouter (Anti-429 & Fallback)

**Label** : `Dev 2` · `Sprint 2` · `LLM`

**Description**
Encaisser les erreurs de quota et réessayer automatiquement sans interrompre l'agent.
Fichiers cibles : `src/llm/token_manager.py`, `src/llm/router.py`

**`TokenRotator`** dans `src/llm/token_manager.py`
- `__init__(env_prefix: str)` : charge `{PREFIX}`, `{PREFIX}_1`, `{PREFIX}_2`, ... depuis `os.environ`
- `get_active_key() -> str`
- `rotate_key() -> str` : bascule sur la clé suivante disponible
- `mark_exhausted(key: str, cooldown_seconds: int = 3600) -> None`

**`LLMRouter`** dans `src/llm/router.py`
- `__init__(primary_client: BaseLLMClient, fallback_clients: list[BaseLLMClient] = [], max_retries: int = 3)`
- `async query(messages: list[dict], stop_sequences: Optional[list[str]] = None) -> tuple[LLMResponse, int]` : retourne `(response, retries_count)`; sur HTTP 429, appelle `token_rotator.rotate_key()` et réessaie; sur erreur persistante, bascule sur `fallback_clients`

**Critères d'acceptation**
- [ ] Simulation HTTP 429 → `rotate_key()` appelé → requête réussie → `retries_count == 1`
- [ ] Si toutes les clés sont épuisées → `LLMQuotaExhaustedError` levée
- [ ] Le `retries_count` retourné correspond exactement au nombre de tentatives supplémentaires effectuées

---

## [S2-DEV2-03] Extraction Multi-Formats & Plafonds Durs MBPP

**Label** : `Dev 2` · `Sprint 2` · `Agent`

**Description**
Accepter toutes les syntaxes de sortie LLM et respecter les limites strictes MBPP.
Fichiers cibles : `src/core/extraction.py` (enrichissement), `src/core/loop.py` (enrichissement)

**Enrichir `CodeExtractor`** dans `src/core/extraction.py`
- `_parse_xml_tool_call(text) -> Optional[CodeExtractionResult]` : `<invoke name="f"><parameter name="x">val</parameter></invoke>` → `f(x=val)`
- `_parse_hermes_json(text) -> Optional[CodeExtractionResult]` : `<tool_call>{"name":"f","arguments":{...}}</tool_call>` → `f(**{...})`
- `_parse_react_format(text) -> Optional[CodeExtractionResult]` : `Action: f\nAction Input: {...}` → `f(**{...})`

**Enrichir `AgentLoop._enforce_hard_limits()`** dans `src/core/loop.py`
- Plafonds MBPP stricts : 10 itérations max, 6 000 tokens input cumulés, 1 500 tokens output cumulés, 120 secondes globales
- Lève `MaxIterationsReachedError` ou `TokenLimitExceededError` selon le dépassement

**Critères d'acceptation**
- [ ] `test_code_extraction.py` : 4 tests (un par format) passent tous
- [ ] Un run MBPP s'arrête automatiquement à l'itération 10 et produit `solution.json` avec `success: false` et `MaxIterationsReachedError` dans `error`
- [ ] Un run MBPP s'arrête si les tokens cumulés dépassent 6 000 en entrée

---

# 🔵 SPRINT 3 — Extension SWE-bench
> Fin de sprint : L'agent corrige de manière autonome au moins 1 bug SWE-bench et produit un patch `git diff` valide.

---

## [S3-DEV1-01] SWEBenchToolKit : Outils Fichiers & Recherche de Code

**Label** : `Dev 1` · `Sprint 3` · `Outils`

**Description**
Implémenter les 6 outils de navigation et modification de code dans le testbed.
Fichier cible : `src/tools/swebench.py` (partie 1)

**`SWEBenchToolKit`** (partie 1)
- `__init__(workspace_root: Optional[Path] = None)` : utilise `Path(os.environ.get("TESTBED_PATH", "."))` si pas de paramètre
- `read_file(filepath: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str` : sortie format strict `cat -n` : chaque ligne préfixée par `<n>: ` avec alignement
- `edit_file(filepath: str, old_str: str, new_str: str) -> str` : remplace la première occurrence exacte de `old_str` par `new_str`; retourne un message d'erreur si `old_str` non trouvé
- `list_files(directory: str, pattern: Optional[str] = None) -> list[str]` : chemins absolus, filtrage glob optionnel
- `search_code(pattern: str, file_pattern: Optional[str] = None) -> str` : grep récursif; format de sortie strict `/absolute/path/file.py:42 <line content>`
- `search_function_or_class_definition_in_code(name: str) -> str` : retourne le fichier et le numéro de ligne de la définition `def name` ou `class name`
- `find_references(name: str, filepath: str, line: int) -> str` : retourne toutes les lignes contenant `name` avec leur chemin et numéro de ligne

**Critères d'acceptation**
- [ ] `read_file("file.py")` : chaque ligne commence par son numéro aligné à droite suivi de `: `
- [ ] `edit_file("file.py", "foo", "bar")` : le fichier est modifié sur disque
- [ ] `edit_file("file.py", "NONEXISTENT", "bar")` : retourne un message d'erreur sans modifier le fichier
- [ ] `search_code("def run")` : chaque ligne de résultat est au format `/abs/path/file.py:12 def run(...):`
- [ ] Les 6 outils passent les tests unitaires de `test_mandatory_tools.py`

---

## [S3-DEV1-02] SWEBenchToolKit : Exécution & Git Diff

**Label** : `Dev 1` · `Sprint 3` · `Outils`

**Description**
Implémenter les 3 outils d'exécution et d'extraction du patch final.
Fichier cible : `src/tools/swebench.py` (partie 2)

**`SWEBenchToolKit`** (partie 2, ajout à la classe)
- `run_tests() -> str` : exécute le script d'évaluation dans `self.workspace_root`; retourne stdout + stderr combinés
- `get_patch() -> str` : exécute `git -c core.fileMode=false diff` depuis `self.workspace_root`; retourne le diff unifié brut
- `run_command(command: str, workdir: Optional[str] = None) -> dict` : exécute via `subprocess.run`; retourne `{"stdout": str, "stderr": str, "exit_code": int}`

**Critères d'acceptation**
- [ ] Après `edit_file()`, `get_patch()` retourne un diff non vide au format unified diff
- [ ] `run_command("echo hello")` retourne `{"stdout": "hello\n", "stderr": "", "exit_code": 0}`
- [ ] `run_command("exit 1")` retourne `{"exit_code": 1}`
- [ ] Les 3 outils passent les tests unitaires de `test_mandatory_tools.py`

---

## [S3-DEV1-03] Serveur MCP SWE-bench & Transport HTTP SSE

**Label** : `Dev 1` · `Sprint 3` · `MCP`

**Description**
Exposer les 9 outils SWE-bench via MCP et enrichir le client pour supporter le transport HTTP SSE.
Fichiers cibles : `mcp_tools_swebench.py`, `src/mcp/client.py` (enrichissement), `src/mcp/tools.py` (enrichissement)

**`SWEBenchMCPServer`** dans `mcp_tools_swebench.py`
- `__init__(testbed_path: Optional[str] = None)` : instancie `SWEBenchToolKit(workspace_root=...)`
- `register_tools() -> None` : enregistre les 9 outils
- `run(transport: str = "stdio", host: str = "127.0.0.1", port: int = 8000) -> None`
- `@classmethod main() -> None`

**Enrichir `MCPClient`** dans `src/mcp/client.py`
- `async connect_http(url: str) -> None` : connexion HTTP SSE

**Enrichir `MCPToolManager`** dans `src/mcp/tools.py`
- `generate_markdown_manual(tools: list[MCPToolDefinition]) -> str` : génère la doc des outils pour le system prompt

**Critères d'acceptation**
- [ ] `python mcp_tools_swebench.py` démarre sans erreur
- [ ] Le client MCP peut appeler `read_file` via le serveur SWE-bench
- [ ] Le manuel généré liste correctement les 9 outils avec leurs paramètres
- [ ] `MCPClient.connect_http("http://localhost:8000")` se connecte sans erreur

---

## [S3-DEV2-01] Docker Lifecycle & CLI agent_swebench

**Label** : `Dev 2` · `Sprint 3` · `Infrastructure`

**Description**
Gérer le cycle de vie du conteneur Docker et créer le script d'évaluation SWE-bench.
Fichier cible : `agent_swebench.py`

**`SWEBenchAgentApp`** dans `agent_swebench.py`
- `__init__(args=None)` : parse `--task-file`, `--output`, `--model-name`, `--provider-url`, `--max-iterations`
- `load_task() -> SWEBenchTaskInput`
- `setup_docker_environment() -> None` : `docker run -d {docker_image}`, configure `TESTBED_PATH`, enregistre `signal.signal(signal.SIGTERM, cleanup)` et `atexit.register(cleanup)`
- `cleanup_docker_environment() -> None` : `docker stop` + `docker rm`
- `execute() -> SolutionOutput`
- `save_solution(solution: SolutionOutput) -> None`
- `@classmethod main() -> None` : bloc `try...finally` garantissant `cleanup_docker_environment()`

**Critères d'acceptation**
- [ ] Le script démarre un conteneur Docker, vérifie qu'il tourne, exécute l'agent
- [ ] `Ctrl+C` pendant l'exécution → le conteneur est arrêté et supprimé proprement
- [ ] Le script retourne le code 0 si `solution.success == True`, 1 sinon
- [ ] Pas de conteneur orphelin après chaque exécution (vérifiable avec `docker ps -a`)

---

## [S3-DEV2-02] Plafonds SWE-bench & Modèle SWEBenchTaskInput

**Label** : `Dev 2` · `Sprint 3` · `Agent`

**Description**
Charger les tâches SWE-bench et appliquer ses plafonds spécifiques dans la boucle.
Fichiers cibles : `src/models/tasks.py` (enrichissement), `src/core/loop.py` (enrichissement)

**`SWEBenchTaskInput(BaseModel)`** dans `src/models/tasks.py`
- Champs : `instance_id: str`, `problem_statement: str`, `docker_image: str`, `eval_script: str`, `hints_text: str = ""`, `repo: str = ""`

**Enrichir `AgentLoop._enforce_hard_limits()`**
- Plafonds SWE-bench : 30 itérations, 300 000 tokens input cumulés, 10 000 tokens output cumulés, 900 secondes globales
- La convention de réponse réussie est `final_answer(get_patch())` : le champ `SolutionOutput.solution` contient le patch git

**Critères d'acceptation**
- [ ] `SWEBenchTaskInput.model_validate(json.loads(task_file))` parse sans erreur le fichier de tâche de la moulinette
- [ ] Un run SWE-bench dépassant 30 itérations produit `solution.json` avec `success: false` et l'erreur appropriée
- [ ] `SolutionOutput.solution` contient un diff `git` valide quand l'agent termine avec succès

---

## [S3-DEV2-03] Prompt SWE-bench & Client Gemini

**Label** : `Dev 2` · `Sprint 3` · `LLM`

**Description**
Adapter le system prompt au contexte de recherche de bugs et ajouter Gemini comme provider de secours.
Fichiers cibles : `src/core/prompt.py` (enrichissement), `src/llm/gemini.py`

**Enrichir `PromptManager.build_system_prompt()`**
- Inclure les instructions SWE-bench : explorer le code en premier, lire les tests existants, modifier de façon chirurgicale, terminer avec `final_answer(get_patch())`

**`GeminiClient(BaseLLMClient)`** dans `src/llm/gemini.py`
- `async generate(messages, stop_sequences) -> LLMResponse` : appel via l'API REST Gemini ou `google-genai` SDK

**Critères d'acceptation**
- [ ] Le system prompt SWE-bench mentionne explicitement `get_patch()` et `final_answer()`
- [ ] `GeminiClient` retourne une `LLMResponse` valide avec un vrai modèle Gemini
- [ ] Le `LLMRouter` accepte `GeminiClient` en fallback si les providers OpenAI-compatible sont épuisés

---

# 📊 SPRINT 4 — Benchmarks, Rapport & Soutenance
> Fin de sprint : Rapports complets et conformes au Chapitre V.7, prêts pour la présentation.

---

## [S4-TEAM-01] Campagne de Benchmark : 5 Modèles × 3 Tâches

**Label** : `Dev 1 + Dev 2` · `Sprint 4` · `Benchmark`

**Description**
Évaluer l'agent sur un panel représentatif de modèles et collecter les preuves d'évaluation.
Répertoire cible : `benchmark_artifacts/`

Tâches SWE-bench recommandées : `sympy__sympy-14711`, `sympy__sympy-13480`, `xarray__xarray-4629`
Modèles exemples : `llama-3.1-8b`, `llama-3.1-70b`, `gemma-2-9b`, `mixtral-8x7b`, `gemini-1.5-flash`
Providers : Groq et OpenRouter (au moins 2 différents)

Organisation des artefacts :
```
benchmark_artifacts/
├── sympy__sympy-14711/
│   ├── llama-3.1-8b_solution.json
│   ├── llama-3.1-70b_solution.json
│   └── ...
├── sympy__sympy-13480/
│   └── ...
└── xarray__xarray-4629/
    └── ...
```

**Critères d'acceptation**
- [ ] 15 fichiers `solution.json` présents (5 modèles × 3 tâches)
- [ ] Chaque `solution.json` est valide (parseable par Pydantic sans erreur)
- [ ] Au moins 2 providers différents utilisés (vérifiable dans `api_url` des `StepMetrics`)
- [ ] Les `solution.json` incluent les champs `steps`, `total_input_tokens`, `total_time_seconds`

---

## [S4-TEAM-02] Métriques Intermédiaires & Ablation Study

**Label** : `Dev 2 pilote` · `Sprint 4` · `Analyse`

**Description**
Calculer des indicateurs de qualité de raisonnement et mener une expérience comparative.
Résultats à consigner dans `BENCHMARK_REPORT.md`

**Métriques intermédiaires à calculer** pour chaque run :
- Étape du premier appel à `read_file` sur le fichier impliqué dans le bug
- Étape du premier appel à `run_tests`
- Étape où `run_tests` retourne moins d'échecs qu'au départ

**Ablation study** : comparer deux configurations, par exemple :
- Version A : avec `search_code` disponible
- Version B : sans `search_code` (outil retiré du serveur MCP)

**Critères d'acceptation**
- [ ] Tableau des métriques intermédiaires rempli pour au moins 3 runs
- [ ] Au moins une ablation documentée avec 2 résultats chiffrés à comparer
- [ ] Les données sont issues des vrais `solution.json` (pas de valeurs inventées)

---

## [S4-TEAM-03] Rédaction BENCHMARK_REPORT.md

**Label** : `Dev 2 pilote` · `Sprint 4` · `Documentation`

**Description**
Rédiger le rapport comparatif complet conformément au Chapitre V.7 du sujet.
Fichier cible : `BENCHMARK_REPORT.md`

Contenu attendu :
1. **Introduction** : Choix des tâches et des modèles, explication de la méthodologie
2. **Tableau de résultats principaux** : Modèle, provider, succès (✅/❌), tokens consommés, latence moyenne, retries
3. **Tableau des métriques intermédiaires** : Étapes de première lecture, premier test, première amélioration
4. **Ablation Study** : Résultats avec et sans l'outil comparé, analyse de l'impact
5. **Conclusion** : Quel modèle/provider recommander et pourquoi

**Critères d'acceptation**
- [ ] Le rapport contient au minimum 2 tableaux de données numériques
- [ ] La section Ablation Study présente deux résultats chiffrés comparables
- [ ] La conclusion argumente un choix de modèle avec des données à l'appui
- [ ] Le fichier est en Markdown valide et lisible sur GitHub

---

## [S4-TEAM-04] Rédaction README.md (Chapitre VII)

**Label** : `Dev 1 pilote` · `Sprint 4` · `Documentation`

**Description**
Rédiger la documentation principale conforme aux exigences du Chapitre VII du sujet.
Fichier cible : `README.md`

Sections obligatoires :
1. Première phrase en italique 42 (*"As a 42 student..."*)
2. Description de l'architecture et de la boucle agentique
3. Explication du sandbox et de ses mécanismes de sécurité
4. Liste et description des outils disponibles (MBPP et SWE-bench)
5. Instructions de lancement :
   - `uv run sandbox sandbox_template.json --mcp-stdio "python mcp_tools_mbpp.py"`
   - `uv run python -m agent_mbpp --task-file <PATH> --output <PATH> --model-name <NAME> --provider-url <URL>`
   - `uv run python -m agent_swebench --task-file <PATH> --output <PATH> --model-name <NAME> --provider-url <URL>`

**Critères d'acceptation**
- [ ] La première phrase du README est en italique et commence par *"As a 42 student..."*
- [ ] Les 3 commandes de lancement sont présentes et syntaxiquement correctes
- [ ] La section Sandbox explique au moins 3 mécanismes de sécurité (imports, réseau, mémoire)
- [ ] Le README est rédigé intégralement en anglais
