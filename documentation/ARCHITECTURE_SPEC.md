# Spécification d'Architecture Détaillée (Version Consolidée) — Agent Smith

Ce document définit l'architecture logicielle complète du projet **Agent Smith** (version 1.1), alignée sur la structure consolidée de `STRUCTURE.md`. Il applique une conception **Orientée Objet modulaire et pragmatique**, garantissant le principe de responsabilité unique (SRP) et la préparation optimale à l'examen (live coding 2-5 min et tests de la moulinette).

---

## 1. Fichiers Racines et Points d'Entrée CLI

### `pyproject.toml`
* **Rôle** : Configuration du projet Python 3.10 géré par `uv`. Déclare les dépendances (`pydantic>=2.0`, `mcp`, `httpx`, `pytest`, `ruff`, etc.) et le point d'entrée CLI pour la sandbox :
  ```toml
  [project.scripts]
  sandbox = "src.sandbox.cli:SandboxCLIApp.main"
  ```

### `.env.example`
* **Rôle** : Modèle documentant l'ensemble des variables d'environnement requises (clés API providers `OPENROUTER_API_KEY`, `GROQ_API_KEY`, etc. et `TESTBED_PATH`).

### `sandbox_template.json`
* **Rôle** : Fichier modèle de configuration par défaut sérialisé depuis `SandboxConfig`.

### `mcp_tools_mbpp.py`
* **Rôle** : Point d'entrée serveur MCP MBPP imposé à la racine du dépôt (*Section V.2.4*).
* **Classes & Méthodes** :
  * `class MBPPMCPServer`:
    * `__init__(toolkit: Optional[MBPPToolKit] = None)` : Instancie le serveur MCP et injecte le toolkit MBPP.
    * `register_tools() -> None` : Enregistre l'outil `run_tests(code: str, test_list: list[str])`.
    * `run(transport: str = "stdio", host: str = "127.0.0.1", port: int = 8000) -> None` : Démarre l'écoute (stdio ou streamable HTTP).
    * `@classmethod main() -> None` : Point d'entrée d'exécution CLI.

### `mcp_tools_swebench.py`
* **Rôle** : Point d'entrée serveur MCP SWE-bench imposé à la racine du dépôt (*Section V.2.4 & V.5*).
* **Classes & Méthodes** :
  * `class SWEBenchMCPServer`:
    * `__init__(testbed_path: Optional[str] = None)` : Résout `TESTBED_PATH` et initialise `FileTools`, `SearchTools`, et `ExecutionTools`.
    * `register_tools() -> None` : Enregistre les 9 outils obligatoires (filesystem, search, execution).
    * `run(transport: str = "stdio", host: str = "127.0.0.1", port: int = 8000) -> None` : Démarre l'écoute (stdio ou HTTP SSE).
    * `@classmethod main() -> None` : Point d'entrée d'exécution CLI.

### `agent_mbpp.py`
* **Rôle** : Point d'entrée CLI exécuté lors de l'évaluation : `uv run python -m agent_mbpp ...` (*Section V.3.1*).
* **Classes & Méthodes** :
  * `class MBPPAgentApp`:
    * `__init__(args: Optional[argparse.Namespace] = None)` : Parse les options en ligne de commande (`--task-file`, `--output`, `--model-name`, `--provider-url`, `--max-iterations`).
    * `run() -> int` : Délègue l'exécution à `MBPPAgent` (`src/agent/mbpp_agent.py`) et retourne le code de sortie (0 en cas de succès, 1 sinon).
    * `@classmethod main() -> None` : Point d'entrée système.

### `agent_swebench.py`
* **Rôle** : Point d'entrée CLI exécuté lors de l'évaluation : `uv run python -m agent_swebench ...` (*Section V.4.1*).
* **Classes & Méthodes** :
  * `class SWEBenchAgentApp`:
    * `__init__(args: Optional[argparse.Namespace] = None)` : Parse les options CLI SWE-bench.
    * `run() -> int` : Délègue l'exécution à `SWEBenchAgent` (`src/agent/swebench_agent.py`) avec gestion garantie du nettoyage Docker.
    * `@classmethod main() -> None` : Point d'entrée système.

---

## 2. Package `src/models/` (Modèles de Données Pydantic v2)

### `src/models/config.py`
* **Rôle** : Configuration et validation des limites et permissions du bac à sable (*Section V.2*).
* **Classes & Méthodes** :
  * `class SandboxConfig(BaseModel)` :
    * Attributs : `authorized_imports: list[str]`, `allowed_directories: list[str]`, `max_execution_time_seconds: int = 30`, `max_memory_mb: int = 512`.
    * `is_import_authorized(module_name: str) -> bool` : Vérifie l'allowlist (supporte les wildcards comme `collections.*`).
    * `is_path_authorized(path: str | Path) -> bool` : Résout le chemin canonique réel (`realpath`) et valide son inclusion dans `allowed_directories`.
    * `@classmethod from_json_file(file_path: Path) -> SandboxConfig` : Charge et valide un fichier JSON de configuration.

### `src/models/tasks.py`
* **Rôle** : Schémas des tâches de test fournis par la moulinette (*Sections V.3.3 & V.4.3*).
* **Classes** :
  * `class MBPPTaskInput(BaseModel)` : `task_id: int`, `task_definition: str`, `function_definition: str`, `test_imports: list[str]`, `test_list: list[str]`.
  * `class SWEBenchTaskInput(BaseModel)` : `instance_id: str`, `problem_statement: str`, `docker_image: str`, `eval_script: str`, `hints_text: str = ""`, `repo: str = ""`.

### `src/models/metrics.py`
* **Rôle** : Modèles stricts pour la journalisation des pas et la validation du résultat (*Section V.1.1*).
* **Classes & Méthodes** :
  * `class StepMetrics(BaseModel)` :
    * Attributs : `step: int`, `input_tokens: int`, `output_tokens: int`, `request_time_ms: float`, `timestamp: str`, `api_url: str`, `model_name: str`, `llm_output: str`, `sandbox_input: str`, `sandbox_output: str`, `retries: int`.
  * `class SolutionOutput(BaseModel)` :
    * Attributs : `task_id: str`, `benchmark: str`, `success: bool`, `solution: str`, `iterations: int`, `total_requests: int`, `total_input_tokens: int`, `total_output_tokens: int`, `total_time_seconds: float`, `steps: list[StepMetrics]`, `system_prompt: str`, `error: Optional[str]`, `timestamp: str`.
    * `record_step(step: StepMetrics) -> None` : Met à jour les compteurs cumulés (tokens, temps, requêtes).
    * `to_file(path: Path) -> None` : Sérialise et sauvegarde le résultat en JSON conforme pour la moulinette.

---

## 3. Package `src/core/` (Moteur de Raisonnement & Infrastructure Transversale)

### `src/core/exceptions.py`
* **Rôle** : Hiérarchie centralisée des exceptions typées garantissant la tolérance aux pannes sans masquer les signaux système (`KeyboardInterrupt`, `SystemExit`) (*Section IV.1 & V.2.2*).
* **Classes** :
  * `class AgentSmithException(Exception)` : Exception racine pour toutes les erreurs gérées.
    * `to_log_message() -> str` : Message d'erreur formaté.
  * `class SandboxSecurityError(AgentSmithException)` : Violation de sécurité (import, path restrict, network).
  * `class SandboxTimeoutError(AgentSmithException)` : Dépassement de `max_execution_time_seconds` (30s).
  * `class SandboxMemoryError(AgentSmithException)` : Dépassement du quota RAM `max_memory_mb`.
  * `class MCPCommunicationError(AgentSmithException)` : Rupture de communication ou erreur RPC MCP.
  * `class LLMQuotaExhaustedError(AgentSmithException)` : Toutes les clés API ont épuisé leur quota (429 persistant).
  * `class TokenLimitExceededError(AgentSmithException)` : Dépassement des plafonds hard de tokens cumulés.
  * `class MaxIterationsReachedError(AgentSmithException)` : Limite d'itérations atteinte sans `final_answer()`.

### `src/core/logger.py`
* **Rôle** : Journalisation standardisée dirigée vers `sys.stderr` pour ne jamais polluer le flux `sys.stdout` utilisé par la sandbox et la moulinette.
* **Fonctions** :
  * `setup_logging(level: str = "INFO", log_file: Optional[Path] = None) -> None` : Configure le logging Python natif avec `StreamHandler(sys.stderr)` et formatage horodaté. Tous les modules appellent ensuite `logging.getLogger(__name__)`.

### `src/core/extraction.py`
* **Rôle** : Extraction robuste et conversion de code depuis les réponses LLM multi-formats (*Section V.1*).
* **Classes & Méthodes** :
  * `class CodeExtractionResult(BaseModel)` : `code: str`, `was_malformed: bool`, `explanation: str`, `format_detected: str`.
  * `class CodeExtractor`:
    * `extract(response_text: str) -> CodeExtractionResult` : Analyse le texte et orchestre la conversion vers du code Python.
    * `_extract_python_block(text: str) -> Optional[CodeExtractionResult]` : Blocs ```python ... ``` ou ``` ... <end_code>.
    * `_parse_xml_tool_call(text: str) -> Optional[CodeExtractionResult]` : `<invoke name="..."><parameter>...</parameter></invoke>`.
    * `_parse_hermes_json(text: str) -> Optional[CodeExtractionResult]` : `<tool_call>{"name": ..., "arguments": ...}</tool_call>`.
    * `_parse_react_format(text: str) -> Optional[CodeExtractionResult]` : `Action: ... / Action Input: ...`.

### `src/core/prompt.py`
* **Rôle** : Gestion unifiée de la construction des prompts système et du formatage des observations d'étapes.
* **Classes & Méthodes** :
  * `class PromptManager`:
    * `__init__(base_instructions: str)` : Stocke les gabarits de base.
    * `build_system_prompt(tool_manual: str) -> str` : Compile le system prompt intégrant les règles du loop, la commande `final_answer()`, et le manuel dynamique des outils connectés.
    * `format_observation(stdout: str, stderr: str, is_timeout: bool = False, truncated: bool = False, warning_note: Optional[str] = None) -> str` : Structure la réponse du sandbox avec signalement explicite des anomalies (timeout, troncature, lint).

### `src/core/loop.py`
* **Rôle** : Moteur agnostique de la boucle **Thought → Code → Observation**.
* **Classes & Méthodes** :
  * `class AgentLoop`:
    * `__init__(llm_client: BaseLLMClient, sandbox_runner: SandboxRunner, prompt_manager: PromptManager, extractor: CodeExtractor, max_iterations: int, max_input_tokens: int, max_output_tokens: int, timeout_seconds: int)` : Injection de dépendances complète.
    * `run(task_id: str, benchmark: str, user_prompt: str, tool_manual: str) -> SolutionOutput` : Déroule la boucle de raisonnement, vérifie les seuils durs, capture `final_answer()` et enregistre les `StepMetrics`.
    * `_enforce_hard_limits(iteration: int, cumulative_in: int, cumulative_out: int, elapsed_time: float) -> None` : Valide les limites dures du benchmark.

---

## 4. Package `src/agent/` (Orchestrateurs Spécialisés par Benchmark)

### `src/agent/mbpp_agent.py`
* **Rôle** : Orchestrateur dédié à la résolution des tâches algorithmiques MBPP (*Section V.3*).
* **Classes & Méthodes** :
  * `class MBPPAgent`:
    * `__init__(task_file: Path, output_file: Path, model_name: str, provider_url: str, max_iterations: int = 10)`
    * `load_task() -> MBPPTaskInput` : Charge et valide le JSON d'entrée.
    * `bootstrap_environment() -> tuple[SandboxRunner, BaseLLMClient, str]` : Configure le serveur MCP MBPP local, connecte le client MCP, prépare le namespace sandbox et génère le manuel d'outils.
    * `solve() -> SolutionOutput` : Exécute `AgentLoop` avec les limites MBPP (10 iters, 120s, 6k in, 1.5k out).
    * `save_solution(solution: SolutionOutput) -> None` : Sauvegarde le fichier `solution.json`.

### `src/agent/swebench_agent.py`
* **Rôle** : Orchestrateur dédié à la résolution des tâches réelles SWE-bench (*Section V.4*).
* **Classes & Méthodes** :
  * `class SWEBenchAgent`:
    * `__init__(task_file: Path, output_file: Path, model_name: str, provider_url: str, max_iterations: int = 30)`
    * `load_task() -> SWEBenchTaskInput` : Charge la tâche SWE-bench.
    * `bootstrap_environment() -> tuple[SandboxRunner, BaseLLMClient, str]` : Initialise le conteneur Docker via `DockerManager`, démarre le serveur MCP SWE-bench et prépare la sandbox.
    * `solve() -> SolutionOutput` : Exécute `AgentLoop` avec les limites SWE-bench (30 iters, 900s, 300k in, 10k out).
    * `save_solution(solution: SolutionOutput) -> None` : Sauvegarde le fichier `solution.json` avec le git patch dans le champ `solution`.

---

## 5. Package `src/sandbox/` (Environnement d'Exécution Sécurisé Découpé)

Chaque verrou de sécurité est séparé dans un module dédié (principe SRP) pour faciliter la maintenance et les tests unitaires de `exam_sandbox.sh`.

### `src/sandbox/security.py`
* **Rôle** : Analyse syntaxique statique (AST) avant exécution du code.
* **Classes & Méthodes** :
  * `class ASTSecurityAnalyzer`:
    * `__init__(config: SandboxConfig)`
    * `analyze(code: str) -> None` : Parse le code via `ast.parse` et lève `SandboxSecurityError` en cas d'import non autorisé ou de tentative de traversée d'attributs privés/magiques (`__subclasses__`, `__globals__`, etc.).

### `src/sandbox/builtins_guard.py`
* **Rôle** : Whitelist et assainissement du dictionnaire `__builtins__`.
* **Classes & Méthodes** :
  * `class BuiltinsGuard`:
    * `@classmethod get_safe_builtins() -> dict` : Construit un dictionnaire de builtins sans `eval`, `exec`, `breakpoint`, `compile`, etc., avec un `__import__` sécurisé.

### `src/sandbox/fs_guard.py`
* **Rôle** : Restriction des accès au système de fichiers.
* **Classes & Méthodes** :
  * `class FileSystemGuard`:
    * `__init__(config: SandboxConfig)`
    * `safe_open(file: str | Path, mode: str = "r", *args, **kwargs)` : Wrapper de la fonction native `open` vérifiant `config.is_path_authorized(file)`. Lève `SandboxSecurityError` en cas d'accès hors allowlist.

### `src/sandbox/limits.py`
* **Rôle** : Application des quotas mémoire et contrôle des signaux réseau et timeout.
* **Classes & Méthodes** :
  * `class ResourceLimits`:
    * `@classmethod apply_memory_limit(max_memory_mb: int) -> None` : Configure `resource.setrlimit(resource.RLIMIT_AS, ...)` sur le sous-processus.
    * `@classmethod disable_network() -> None` : Neutralise les sockets via `socket.socket` levant systématiquement `PermissionError`.

### `src/sandbox/core.py`
* **Rôle** : Exécution isolée en sous-processus et gestion de `final_answer`.
* **Classes & Méthodes** :
  * `class FinalAnswerSignal(Exception)` : Exception transportant la réponse de l'agent.
  * `class ExecutionResult`: `stdout: str`, `stderr: str`, `exit_code: int`, `final_answer: Optional[str]`, `is_timeout: bool`, `is_truncated: bool`.
  * `class SandboxRunner`:
    * `__init__(config: SandboxConfig, tools_namespace: dict)` : Prépare l'environnement de base et injecte les outils MCP + `final_answer`.
    * `execute(code: str) -> ExecutionResult` : Lance l'exécution dans un sous-processus dédié avec timeout de 30 secondes, redirection I/O, application des verrous AST, builtins, paths, mémoire et réseau.
    * `_truncate_output(output: str, max_chars: int = 4000) -> tuple[str, bool]` : Tronque la sortie avec mention explicite.

### `src/sandbox/cli.py`
* **Rôle** : REPL interactif en ligne de commande pour `uv run sandbox` (*Section V.2.1*).
* **Classes & Méthodes** :
  * `class SandboxCLIApp`:
    * `__init__(argv: Optional[list[str]] = None)` : Parse les arguments CLI (`config.json`, `--mcp-stdio`, `--mcp-server`).
    * `setup_session() -> None` : Initialise la configuration et connecte le transport MCP spécifié.
    * `start_repl() -> None` : Boucle interactive REPL jusqu'à `exit` ou `Ctrl+D` (EOF).
    * `@classmethod main() -> None` : Point d'entrée de commande.

---

## 6. Package `src/mcp/` (Client MCP & Intégration Dynamique Découpée)

### `src/mcp/client.py`
* **Rôle** : Gestion des transports MCP (stdio et HTTP SSE).
* **Classes & Méthodes** :
  * `class MCPToolDefinition(BaseModel)` : `name: str`, `description: str`, `parameters: dict`.
  * `class MCPClient`:
    * `async connect_stdio(command: str) -> None` : Établit la session via sous-processus stdio.
    * `async connect_http(url: str) -> None` : Établit la session via streaming HTTP SSE.
    * `async list_tools() -> list[MCPToolDefinition]` : Récupère la liste des outils exposés par le serveur.
    * `async call_tool(name: str, arguments: dict) -> Any` : Exécute un outil via JSON-RPC.
    * `async close() -> None` : Ferme proprement les connexions et sous-processus.

### `src/mcp/bridge.py`
* **Rôle** : Transformation des définitions d'outils distants en fonctions Python injectables dans le sandbox.
* **Classes & Méthodes** :
  * `class MCPToolBridge`:
    * `__init__(client: MCPClient)`
    * `async create_tool_callables() -> dict[str, Callable]` : Construit à la volée des wrappers Python avec signatures dynamiques adaptées au namespace d'exécution de la sandbox.

### `src/mcp/dynamic_manual.py`
* **Rôle** : Synthèse dynamique de la documentation des outils connectés pour injection dans le system prompt (*Section V.2.5*).
* **Classes & Méthodes** :
  * `class DynamicManualGenerator`:
    * `@classmethod generate(tools: list[MCPToolDefinition]) -> str` : Produit un guide Markdown des outils disponibles avec noms, descriptions, signatures et types.

---

## 7. Package `src/llm/` (Abstraction LLM, Rotation & Métrologie)

### `src/llm/base.py`
* **Rôle** : Contrat d'interface et modèle de réponse commun.
* **Classes & Méthodes** :
  * `class LLMResponse(BaseModel)` : `text: str`, `input_tokens: int`, `output_tokens: int`, `latency_ms: float`, `model_name: str`, `api_url: str`.
  * `class BaseLLMClient(ABC)` :
    * `__init__(model_name: str, base_url: str, api_key: str)`
    * `@abstractmethod async def generate(messages: list[dict], stop_sequences: Optional[list[str]] = None) -> LLMResponse`

### `src/llm/openai_compatible.py`
* **Rôle** : Client générique pour tous les fournisseurs d'API compatibles OpenAI (Groq, OpenRouter, Mistral, Together AI).
* **Classes & Méthodes** :
  * `class OpenAICompatibleClient(BaseLLMClient)`:
    * `async generate(messages: list[dict], stop_sequences: Optional[list[str]] = None) -> LLMResponse` : Effectue la requête HTTP POST sur `{base_url}/chat/completions`, mesure la latence et extrait le décompte de tokens.

### `src/llm/gemini.py`
* **Rôle** : Client dédié pour Google AI Studio / Gemini API (*Section V.6.1*).
* **Classes & Méthodes** :
  * `class GeminiClient(BaseLLMClient)`:
    * `async generate(messages: list[dict], stop_sequences: Optional[list[str]] = None) -> LLMResponse` : Appel via l'API REST Google Gemini ou le SDK officiel.

### `src/llm/key_manager.py`
* **Rôle** : Gestion du pool de clés API, détection des erreurs 429 et rotation automatique (*Section V.6.1 & V.7*).
* **Classes & Méthodes** :
  * `class KeyManager`:
    * `__init__(provider_name: str, env_prefix: str)` : Charge l'ensemble des clés définies (`{PREFIX}`, `{PREFIX}_1`, `{PREFIX}_2`...).
    * `get_active_key() -> str` : Renvoie la clé active.
    * `rotate_key() -> str` : Bascule sur la clé suivante lors de la réception d'une erreur 429.
    * `mark_exhausted(key: str, cooldown_seconds: int = 3600) -> None` : Met une clé en pause sur épuisement du quota journalier.

### `src/llm/token_tracker.py`
* **Rôle** : Mesure du temps d'API (wall-clock ms), décompte précis des tokens d'entrée et de sortie, et gestion des retries avec backoff.
* **Classes & Méthodes** :
  * `class TokenTracker`:
    * `__init__(primary_client: BaseLLMClient, key_manager: KeyManager, fallback_clients: Optional[list[BaseLLMClient]] = None, max_retries: int = 3)`
    * `async query(messages: list[dict], stop_sequences: Optional[list[str]] = None) -> tuple[LLMResponse, int]` : Mesure la latence, incrémente le compteur de retries, effectue la rotation de clé via `KeyManager` sur erreur 429, et bascule sur les clients de repli si nécessaire.

---

## 8. Package `src/tools/` (Outils Métier Découpés par Domaine)

### `src/tools/file_tools.py`
* **Rôle** : Outils de manipulation de fichiers pour SWE-bench (*Section V.5.1*).
* **Classes & Méthodes** :
  * `class FileTools`:
    * `__init__(workspace_root: Path)`
    * `read_file(filepath: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str` : Sortie format `cat -n` strict (`<line_number>: <line_content>`).
    * `edit_file(filepath: str, old_str: str, new_str: str) -> str` : Remplacement exact d'une sous-chaîne.
    * `list_files(directory: str, pattern: Optional[str] = None) -> list[str]` : Liste filtrée par glob.

### `src/tools/search_tools.py`
* **Rôle** : Outils de recherche et exploration de code pour SWE-bench (*Section V.5.2*).
* **Classes & Méthodes** :
  * `class SearchTools`:
    * `__init__(workspace_root: Path)`
    * `search_code(pattern: str, file_pattern: Optional[str] = None) -> str` : Grep récursif au format strict `/path:<line_number> <line_content>`.
    * `search_function_or_class_definition_in_code(name: str) -> str` : Localisation de définitions de classes/fonctions.
    * `find_references(name: str, filepath: str, line: int) -> str` : Détection de tous les usages d'un symbole.

### `src/tools/execution_tools.py`
* **Rôle** : Outils d'exécution de commandes et d'extraction de patch pour SWE-bench (*Section V.5.3*).
* **Classes & Méthodes** :
  * `class ExecutionTools`:
    * `__init__(workspace_root: Path)` : Utilise le chemin du dépôt (`TESTBED_PATH`).
    * `run_tests() -> str` : Exécute le script d'évaluation dans le testbed.
    * `get_patch() -> str` : Récupère le diff unifié via `git -c core.fileMode=false diff`.
    * `run_command(command: str, workdir: Optional[str] = None) -> dict` : Exécute une commande shell et renvoie `{"stdout": str, "stderr": str, "exit_code": int}`.

### `src/tools/mbpp_tools.py`
* **Rôle** : Outil d'évaluation des assertions pour MBPP (*Section V.3.2*).
* **Classes & Méthodes** :
  * `class MBPPToolKit`:
    * `run_tests(code: str, test_list: list[str]) -> str` : Évalue le code avec les assertions de test et retourne une chaîne JSON formatée `{"success": bool, "output": str}`.

### `src/tools/docker_manager.py`
* **Rôle** : Gestion du cycle de vie des conteneurs Docker pour SWE-bench (*Section V.4*).
* **Classes & Méthodes** :
  * `class DockerManager`:
    * `__init__(image_name: str, instance_id: str)`
    * `start_container() -> str` : Démarre le conteneur en arrière-plan, configure le testbed et retourne l'identifiant du conteneur.
    * `cleanup_container() -> None` : Arrête et supprime le conteneur. Armé automatiquement via `signal.SIGTERM` et `atexit`.
    * `execute_in_container(command: str) -> tuple[int, str, str]` : Exécute une commande dans le conteneur via `docker exec`.

---

## 9. Package `tests/` (Suites de Tests & Validation)

* **`tests/test_sandbox_security.py`** : Valide l'ensemble des verrous de sécurité (AST statique, builtins assainis, accès fichiers restreints, blocage des sockets réseau, limite de mémoire `resource`, et propagation de `KeyboardInterrupt`).
* **`tests/test_llm_rotation.py`** : Valide la détection du code 429, la rotation transparente de clé via `KeyManager` et le fallback sans interruption de l'agent.
* **`tests/test_code_extractor.py`** : Valide la conversion des formats Markdown, XML Anthropic, JSON Hermes et ReAct en blocs Python exécutables.
* **`tests/test_mcp_tools.py`** : Valide unitairement les formats stricts des 9 outils obligatoires (`cat -n`, grep formaté, `git diff`).
* **`tests/test_mbpp_loop.py`** : Test d'intégration de bout en bout de la boucle ReAct sur une tâche MBPP simulée.
