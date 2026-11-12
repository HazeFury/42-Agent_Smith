# Spécification d'Architecture Détaillée (POO) — Agent Smith

Ce document définit l'architecture logicielle complète du projet **Agent Smith** (version 1.1). Il applique une approche **Orientée Objet pragmatique** : chaque classe possède une responsabilité réelle liée à la gestion d'un état ou d'un cycle de vie, sans sur-engineering (élimination des patterns Java-esques, des clones de classes de providers et des fichiers d'une poignée de lignes).

---

## 1. Fichiers Racines et Applications d'Entrée

### `pyproject.toml`
* **Rôle** : Configuration du projet géré par `uv`, ciblant Python 3.10. Déclare les dépendances (`pydantic>=2.0`, `mcp`, `httpx`, `pytest`, `ruff`, etc.) et le point d'entrée CLI :
  ```toml
  [project.scripts]
  sandbox = "agent_smith.sandbox.cli:SandboxCLIApp.main"
  ```

### `sandbox_template.json`
* **Rôle** : Configuration JSON par défaut du sandbox, sérialisée depuis `SandboxConfig`.

### `mcp_tools_mbpp.py`
* **Rôle** : Serveur MCP racine pour MBPP (*Section V.2.4*), encapsulé dans une classe dédiée.
* **Classes & Méthodes** :
  * `class MBPPMCPServer`:
    * `__init__(toolkit: Optional[MBPPToolKit] = None)` : Initialise le serveur MCP et injecte le toolkit MBPP.
    * `register_tools() -> None` : Enregistre l'outil `@tool run_tests(code: str, test_list: list[str])`.
    * `run(transport: str = "stdio", host: str = "127.0.0.1", port: int = 8000) -> None` : Démarre le serveur en mode stdio ou HTTP streaming.
    * `@classmethod main() -> None` : Méthode d'entrée CLI avec parsing des arguments.

### `mcp_tools_swebench.py`
* **Rôle** : Serveur MCP racine pour SWE-bench (*Section V.2.4 & V.5*).
* **Classes & Méthodes** :
  * `class SWEBenchMCPServer`:
    * `__init__(testbed_path: Optional[str] = None)` : Résout `TESTBED_PATH` depuis l'environnement et instancie `SWEBenchToolKit`.
    * `register_tools() -> None` : Enregistre les 9 outils obligatoires auprès du serveur MCP.
    * `run(transport: str = "stdio", host: str = "127.0.0.1", port: int = 8000) -> None` : Démarre l'écoute stdio ou HTTP SSE.
    * `@classmethod main() -> None` : Méthode d'entrée CLI.

### `agent_mbpp.py`
* **Rôle** : Application CLI exécutée par la moulinette : `uv run python -m agent_mbpp ...` (*Section V.3.1*).
* **Classes & Méthodes** :
  * `class MBPPAgentApp`:
    * `__init__(args: Optional[argparse.Namespace] = None)` : Parse les arguments CLI (`--task-file`, `--output`, `--model-name`, `--provider-url`, `--max-iterations`).
    * `load_task() -> MBPPTaskInput` : Charge le JSON de la tâche via Pydantic.
    * `bootstrap_environment() -> tuple[SandboxRunner, BaseLLMClient]` : Initialise la sandbox connectée aux outils MBPP et le client LLM.
    * `execute() -> SolutionOutput` : Déroule la boucle `AgentLoop` et gère les exceptions internes.
    * `save_solution(solution: SolutionOutput) -> None` : Exporte le JSON `solution.json`.
    * `@classmethod main() -> None` : Point d'entrée assurant le code de retour et évitant tout crash non géré.

### `agent_swebench.py`
* **Rôle** : Application CLI exécutée par la moulinette : `uv run python -m agent_swebench ...` (*Section V.4.1*).
* **Classes & Méthodes** :
  * `class SWEBenchAgentApp`:
    * `__init__(args: Optional[argparse.Namespace] = None)` : Parse les arguments CLI SWE-bench.
    * `load_task() -> SWEBenchTaskInput` : Charge la tâche et métadonnées Docker.
    * `setup_docker_environment() -> None` : Démarre le conteneur Docker cible, configure `TESTBED_PATH` et arme les handlers de signaux (SIGTERM / SIGKILL).
    * `cleanup_docker_environment() -> None` : Assure l'arrêt et la suppression des conteneurs après exécution.
    * `execute() -> SolutionOutput` : Déroule l'agent loop et récupère le git diff via `final_answer`.
    * `save_solution(solution: SolutionOutput) -> None` : Écrit le `solution.json`.
    * `@classmethod main() -> None` : Point d'entrée principal avec bloc `try...finally` garantissant `cleanup_docker_environment()`.

---

## 2. Package `agent_smith.models` (Modèles de Données Pydantic)

### `agent_smith/models/metrics.py`
* **Rôle** : Modèles de données d'évaluation imposés par la moulinette (*Section V.1.1*).
* **Classes & Méthodes** :
  * `class StepMetrics(BaseModel)` :
    * Attributs stricts : `step: int`, `input_tokens: int`, `output_tokens: int`, `request_time_ms: float`, `timestamp: str`, `api_url: str`, `model_name: str`, `llm_output: str`, `sandbox_input: str`, `sandbox_output: str`, `retries: int`.
  * `class SolutionOutput(BaseModel)` :
    * Attributs stricts : `task_id: str`, `benchmark: str`, `success: bool`, `solution: str`, `iterations: int`, `total_requests: int`, `total_input_tokens: int`, `total_output_tokens: int`, `total_time_seconds: float`, `steps: List[StepMetrics]`, `system_prompt: str`, `error: Optional[str]`, `timestamp: str`.
    * `record_step(step: StepMetrics) -> None` : Met à jour les compteurs cumulés (tokens, temps, requêtes).
    * `to_file(path: Path) -> None` : Exporte le JSON conforme pour validation.

### `agent_smith/models/sandbox.py`
* **Rôle** : Configuration et validation des règles de la sandbox (*Section V.2*).
* **Classes & Méthodes** :
  * `class SandboxConfig(BaseModel)` :
    * Attributs : `authorized_imports: List[str]`, `allowed_directories: List[str]`, `max_execution_time_seconds: int = 30`, `max_memory_mb: int = 512`.
    * `is_import_authorized(module_name: str) -> bool` : Vérifie l'allowlist (syntaxe `.*` comme `collections.*`).
    * `is_path_authorized(path: str | Path) -> bool` : Résout le chemin canonique réel (`realpath`) et vérifie son inclusion dans `allowed_directories`.
    * `@classmethod from_json_file(file_path: Path) -> "SandboxConfig"` : Charge une configuration depuis un fichier JSON.

### `agent_smith/models/tasks.py`
* **Rôle** : Structures typées pour les données d'entrée fournies par la moulinette.
* **Classes** :
  * `class MBPPTaskInput(BaseModel)` : `task_id: int`, `task_definition: str`, `function_definition: str`, `test_imports: List[str]`, `test_list: List[str]`.
  * `class SWEBenchTaskInput(BaseModel)` : `instance_id: str`, `problem_statement: str`, `docker_image: str`, `eval_script: str`, `hints_text: str = ""`, `repo: str = ""`.

---

## 3. Package `agent_smith.core` (Boucle de Raisonnement, Prompts, Logs & Erreurs)

### `agent_smith/core/exceptions.py`
* **Rôle** : Hiérarchie centralisée des exceptions typées garantissant la tolérance aux pannes (*Section IV.1*) sans masquer les signaux système (`KeyboardInterrupt`, `SystemExit`).
* **Classes** :
  * `class AgentSmithException(Exception)` : Exception racine pour toutes les erreurs gérées.
    * `to_log_message() -> str` : Message formaté pour les logs et le rapport d'échec.
  * `class SandboxSecurityError(AgentSmithException)` : Violation de sécurité (import, path restrict, network).
  * `class SandboxTimeoutError(AgentSmithException)` : Dépassement de `max_execution_time_seconds` (30s).
  * `class SandboxMemoryError(AgentSmithException)` : Dépassement du quota RAM `max_memory_mb`.
  * `class MCPCommunicationError(AgentSmithException)` : Rupture de connexion ou erreur RPC MCP.
  * `class LLMQuotaExhaustedError(AgentSmithException)` : Toutes les clés API ont épuisé leur quota (429 persistant).
  * `class TokenLimitExceededError(AgentSmithException)` : Dépassement des plafonds hard cumulés de tokens.
  * `class MaxIterationsReachedError(AgentSmithException)` : Limite d'itérations atteinte sans `final_answer()`.

### `agent_smith/core/logger.py`
* **Rôle** : Configuration du système de journalisation standard orienté vers `sys.stderr` pour ne **jamais** corrompre le flux `sys.stdout`.
* **Fonctions** :
  * `setup_logging(level: str = "INFO", log_file: Optional[Path] = None) -> None` : Configure le logging Python natif avec `StreamHandler(sys.stderr)` et format standard horodaté. Tous les modules utilisent ensuite simplement `logging.getLogger(__name__)`.

### `agent_smith/core/extraction.py`
* **Rôle** : Extraction robuste et conversion de code depuis les réponses LLM multi-formats (*Section V.1*).
* **Classes & Méthodes** :
  * `class CodeExtractionResult(BaseModel)` : `code: str`, `was_malformed: bool`, `explanation: str`, `format_detected: str`.
  * `class CodeExtractor`:
    * `extract(response_text: str) -> CodeExtractionResult` : Analyse le texte et orchestre la conversion.
    * `_extract_python_block(text: str) -> Optional[CodeExtractionResult]` : Blocs ````python ... ```` ou ```` ... <end_code>`.
    * `_parse_xml_tool_call(text: str) -> Optional[CodeExtractionResult]` : `<invoke name="..."><parameter>...</parameter></invoke>`.
    * `_parse_hermes_json(text: str) -> Optional[CodeExtractionResult]` : `<tool_call>{"name": ..., "arguments": ...}</tool_call>`.
    * `_parse_react_format(text: str) -> Optional[CodeExtractionResult]` : `Action: ... / Action Input: ...`.

### `agent_smith/core/prompt.py`
* **Rôle** : Gestionnaire unifié de la génération des prompts et des retours d'observation.
* **Classes & Méthodes** :
  * `class PromptManager`:
    * `__init__(base_instructions: str)` : Stocke les gabarits de base.
    * `build_system_prompt(tool_manual: str) -> str` : Compile le system prompt intégrant les règles du loop, la commande `final_answer()`, et le manuel dynamique des outils connectés.
    * `format_observation(stdout: str, stderr: str, is_timeout: bool = False, truncated: bool = False, warning_note: Optional[str] = None) -> str` : Structure la réponse du sandbox avec signalement explicite des anomalies (timeout, troncature, lint).

### `agent_smith/core/loop.py`
* **Rôle** : Boucle autonome **Thought → Code → Observation**.
* **Classes & Méthodes** :
  * `class AgentLoop`:
    * `__init__(llm_router: LLMRouter, sandbox_runner: SandboxRunner, prompt_manager: PromptManager, extractor: CodeExtractor, max_iterations: int, max_input_tokens: int, max_output_tokens: int, timeout_seconds: int)` : Injection de dépendances complète.
    * `run(task_id: str, benchmark: str, user_prompt: str, tool_manual: str) -> SolutionOutput` : Déroule la boucle, surveille les seuils durs, capture `final_answer()` et enregistre les `StepMetrics`.
    * `_enforce_hard_limits(iteration: int, cumulative_in: int, cumulative_out: int, elapsed_time: float) -> None` : Valide les limites dures du benchmark.

---

## 4. Package `agent_smith.sandbox` (Environnement d'Exécution Sécurisé)

### `agent_smith/sandbox/security.py`
* **Rôle** : Application stricte des verrous d'isolation en standard library Python pure sans package tiers (*Section V.2.3*).
* **Classes & Méthodes** :
  * `class SecurityEnforcer`:
    * `__init__(config: SandboxConfig)`
    * `install_import_hook() -> None` : Interception de `sys.meta_path` ou `__import__` pour bloquer tout module hors allowlist.
    * `sanitize_builtins() -> dict` : Supprime les builtins dangereux (`eval`, `exec`, `breakpoint`, `compile`) et surcharge `open()` pour restreindre l'accès aux `allowed_directories`.
    * `set_resource_limits() -> None` : Applique les limites mémoire via `resource.setrlimit(resource.RLIMIT_AS, ...)`.
    * `disable_network() -> None` : Surcharge `socket.socket` pour lever systématiquement `PermissionError`.
    * `apply_all_guards() -> dict` : Active l'ensemble des sécurités et retourne le dictionnaire de namespace assaini.

### `agent_smith/sandbox/runner.py`
* **Rôle** : Exécution de code dans un sous-processus isolé, gestion du timeout de 30s, et interception du signal `final_answer`.
* **Classes & Méthodes** :
  * `class FinalAnswerSignal(Exception)` : Exception transportant la réponse passée à `final_answer(answer_string)`.
  * `class ExecutionResult`: `stdout: str`, `stderr: str`, `exit_code: int`, `final_answer: Optional[str]`, `is_timeout: bool`, `is_truncated: bool`.
  * `class SandboxRunner`:
    * `__init__(config: SandboxConfig, tools_namespace: dict)`
    * `execute(code: str) -> ExecutionResult` : Exécute le code dans un sous-processus isolé avec timeout de 30 secondes, redirection des flux I/O et injection du callable `final_answer()`.
    * `_truncate_output(text: str, max_chars: int = 4000) -> tuple[str, bool]` : Tronque la sortie avec message explicite.

### `agent_smith/sandbox/cli.py`
* **Rôle** : Mode interactif REPL conforme à `uv run sandbox` (*Section V.2.1*).
* **Classes & Méthodes** :
  * `class SandboxCLIApp`:
    * `__init__(argv: Optional[list[str]] = None)` : Parse les options (`sandbox_template.json`, `--mcp-stdio`, `--mcp-server`).
    * `setup_session() -> None` : Initialise le sandbox et connecte le transport MCP spécifié.
    * `start_repl() -> None` : Boucle interactive REPL jusqu'à commande `exit` ou `Ctrl+D` (EOF).
    * `@classmethod main() -> None` : Point d'entrée script CLI.

---

## 5. Package `agent_smith.mcp` (Client MCP & Intégration Dynamique)

### `agent_smith/mcp/client.py`
* **Rôle** : Client MCP universel supportant les transports stdio et HTTP SSE.
* **Classes & Méthodes** :
  * `class MCPToolDefinition(BaseModel)` : `name: str`, `description: str`, `parameters: dict`.
  * `class MCPClient`:
    * `__init__()`
    * `async connect_stdio(command: str) -> None` : Démarre le sous-processus stdio et initialise la session.
    * `async connect_http(url: str) -> None` : Initialise la session via streaming HTTP SSE.
    * `async list_tools() -> list[MCPToolDefinition]` : Récupère la liste des outils exposés par le serveur.
    * `async call_tool(name: str, arguments: dict) -> Any` : Exécute un outil via JSON-RPC.
    * `async close() -> None` : Ferme proprement la session et libère les processus.

### `agent_smith/mcp/tools.py`
* **Rôle** : Gestionnaire unifié d'introspection d'outils, conversion en callables Python et génération du manuel LLM (*Section V.2.4 & V.2.5*).
* **Classes & Méthodes** :
  * `class MCPToolManager`:
    * `__init__(client: MCPClient)`
    * `async create_tool_callables() -> dict[str, Callable]` : Génère dynamiquement des fonctions Python avec signatures prêtes à être injectées dans le namespace du sandbox.
    * `generate_markdown_manual(tools: list[MCPToolDefinition]) -> str` : Produit la documentation des outils connectés pour injection dans le system prompt.

---

## 6. Package `agent_smith.tools` (Toolkits Obligatoires Autonomes)

Deux classes de toolkits regroupent les outils obligatoires de manière autonome et directement testable (*Section V.5*).

### `agent_smith/tools/swebench.py`
* **Rôle** : Toolkit regroupant les 9 outils obligatoires pour SWE-bench.
* **Classes & Méthodes** :
  * `class SWEBenchToolKit`:
    * `__init__(workspace_root: Optional[Path] = None)` : Résout le répertoire cible (via paramètre ou variable `TESTBED_PATH`).
    * **Filesystem** :
      - `read_file(filepath: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str` : Sortie format `cat -n` (`<line_number>: <line_content>`).
      - `edit_file(filepath: str, old_str: str, new_str: str) -> str` : Remplacement exact d'une sous-chaîne.
      - `list_files(directory: str, pattern: Optional[str] = None) -> list[str]` : Liste filtrée par glob.
    * **Code Search** :
      - `search_code(pattern: str, file_pattern: Optional[str] = None) -> str` : Grep récursif au format `/path:<line> <content>`.
      - `search_function_or_class_definition_in_code(name: str) -> str` : Localisation de définitions de classes/fonctions.
      - `find_references(name: str, filepath: str, line: int) -> str` : Détection de tous les usages d'un symbole.
    * **Execution** :
      - `run_tests() -> str` : Exécute le script d'évaluation dans `TESTBED_PATH`.
      - `get_patch() -> str` : Récupère le diff via `git -c core.fileMode=false diff`.
      - `run_command(command: str, workdir: Optional[str] = None) -> dict` : Exécute une commande shell et renvoie `{"stdout": str, "stderr": str, "exit_code": int}`.

### `agent_smith/tools/mbpp.py`
* **Rôle** : Toolkit de validation d'assertions pour MBPP (*Section V.3.2*).
* **Classes & Méthodes** :
  * `class MBPPToolKit`:
    * `__init__()`
    * `run_tests(code: str, test_list: list[str]) -> str` : Exécute les assertions de test et retourne une chaîne JSON formatée `{"success": bool, "output": str}`.

---

## 7. Package `agent_smith.llm` (Abstraction LLM & Gestion des Quotas)

### `agent_smith/llm/base.py`
* **Rôle** : Contrat d'interface et modèle de réponse commun.
* **Classes** :
  * `class LLMResponse(BaseModel)` : `text: str`, `input_tokens: int`, `output_tokens: int`, `latency_ms: float`, `model_name: str`, `api_url: str`.
  * `class BaseLLMClient(ABC)` :
    * `__init__(model_name: str, base_url: str, api_key: str)`
    * `@abstractmethod async def generate(messages: list[dict], stop_sequences: Optional[list[str]] = None) -> LLMResponse`

### `agent_smith/llm/openai_compatible.py`
* **Rôle** : Client générique réutilisable pour tous les fournisseurs supportant l'API OpenAI (Groq, OpenRouter, Mistral, Together AI, Perplexity).
* **Classes & Méthodes** :
  * `class OpenAICompatibleClient(BaseLLMClient)`:
    * `async generate(messages: list[dict], stop_sequences: Optional[list[str]] = None) -> LLMResponse` : Effectue l'appel HTTP POST sur `{base_url}/chat/completions` avec calcul précis du temps d'aller-retour et extraction des tokens.

### `agent_smith/llm/gemini.py`
* **Rôle** : Client spécifique pour Google AI Studio / Gemini API (*Section V.6.1*).
* **Classes & Méthodes** :
  * `class GeminiClient(BaseLLMClient)`:
    * `async generate(messages: list[dict], stop_sequences: Optional[list[str]] = None) -> LLMResponse` : Appel via l'API REST Gemini ou le SDK officiel.

### `agent_smith/llm/token_manager.py`
* **Rôle** : Gestion multi-tokens et rotation automatique anti-429 (*Section V.6.1 & V.7*).
* **Classes & Méthodes** :
  * `class TokenRotator`:
    * `__init__(provider_name: str, env_prefix: str)` : Découvre toutes les clés associées (`KEY`, `KEY_1`, `KEY_2`...).
    * `get_active_key() -> str` : Renvoie la clé active courante.
    * `rotate_key() -> str` : Bascule sur la clé suivante lors d'un code HTTP 429.
    * `mark_exhausted(key: str, cooldown_seconds: int = 3600) -> None` : Met une clé en pause sur quota journalier épuisé.

### `agent_smith/llm/router.py`
* **Rôle** : Résilience, gestion des retries avec backoff exponentiel et repli multi-providers.
* **Classes & Méthodes** :
  * `class LLMRouter`:
    * `__init__(primary_client: BaseLLMClient, fallback_clients: Optional[list[BaseLLMClient]] = None, max_retries: int = 3)`
    * `async query(messages: list[dict], stop_sequences: Optional[list[str]] = None) -> tuple[LLMResponse, int]` : Exécute la requête, incrémente le compteur de retries en cas d'erreur transitoire, et bascule sur le client de secours si nécessaire.

---

## 8. Package `tests/` (Suites de Validation)

* **`TestSandboxSecurity` (`tests/test_sandbox_security.py`)** : Teste l'isolation (rejet d'`os`/`sys`, restriction des dossiers, blocage des sockets réseau, limite de mémoire `resource`, non-capture de `KeyboardInterrupt`).
* **`TestMCPProtocol` (`tests/test_mcp_protocol.py`)** : Teste la connexion stdio/HTTP et la génération du manuel d'outils.
* **`TestMandatoryTools` (`tests/test_mandatory_tools.py`)** : Valide unitairement les sorties strictes de `SWEBenchToolKit` et `MBPPToolKit`.
* **`TestCodeExtraction` (`tests/test_code_extraction.py`)** : Valide l'extraction sur les 4 formats (Markdown, XML, Hermes JSON, ReAct).
