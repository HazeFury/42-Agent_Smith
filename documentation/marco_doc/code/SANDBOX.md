# Architecture & Guide Détaillé de la Sandbox (`src/sandbox/core.py`)

Ce document détaille le fonctionnement complet, les choix de conception et le code mis en place dans [`src/sandbox/core.py`](file:///home/marberge/42/projects/agent_smith/src/sandbox/core.py), ainsi que le modèle de données [`ExecutionResult`](file:///home/marberge/42/projects/agent_smith/src/models/models_private.py).

---

## Sommaire

1. [Vue d'ensemble & Problématique](#1-vue-densemble--problématique)
2. [Le modèle `ExecutionResult` (`models_private.py`)](#2-le-modèle-executionresult-models_privatepy)
3. [Architecture IPC & Processus Persistant](#3-architecture-ipc--processus-persistant)
4. [Explication Pas à Pas du Code](#4-explication-pas-à-pas-du-code)
   - [4.1. `_execute_code_in_worker()` : L'exécution et capture locale](#41-_execute_code_in_worker--lexécution-et-capture-locale)
   - [4.2. `_worker_entrypoint()` : La boucle événementielle du processus enfant](#42-_worker_entrypoint--la-boucle-événementielle-du-processus-enfant)
   - [4.3. `SandboxRunner` : Le contrôleur côté processus parent](#43-sandboxrunner--le-contrôleur-côté-processus-parent)
5. [Gestion des Cas Critiques & Sécurité](#5-gestion-des-cas-critiques--sécurité)
   - [Boucles infinies & Timeouts](#boucles-infinies--timeouts)
   - [Crashs mémoires / SIGSEGV & Auto-Recovery](#crashs-mémoires--sigsegv--auto-recovery)
   - [Pourquoi `FinalAnswerSignal` hérite de `BaseException`](#pourquoi-finalanswersignal-hérite-de-baseexception)
6. [Validation & Tests Unitaires](#6-validation--tests-unitaires)

---

## 1. Vue d'ensemble & Problématique

Dans le cadre d'un **Code Agent** (boucle *Thought $\rightarrow$ Code $\rightarrow$ Observation*) et du mode interactif REPL (`uv run sandbox`), l'exécution du code Python pose deux exigences techniques qui semblent au départ contradictoires :

1. **La persistance de l'état** : Si l'agent déclare `data = read_file(...)` à l'étape 1, puis `print(len(data))` à l'étape 2, la variable `data` doit être toujours présente en mémoire. Un simple `subprocess.run(["python", "-c", ...])` ne convient pas car il recrée un processus vierge à chaque tour.
2. **L'isolation et la capacité d'interruption absolue** : Si le LLM génère une boucle infinie (`while True: pass`) ou alloue trop de mémoire, le système doit pouvoir couper net l'exécution sans que le programme principal (l'orchestrateur) ne freeze ni ne crashe. Un simple thread Python ne suffit pas car en Python, le **GIL** (Global Interpreter Lock) empêche de forcer l'arrêt propre d'un thread bloqué.

**La solution retenue :** 
Un **processus enfant dédié persistant** (worker) qui garde son espace de noms (`worker_globals`) en vie, piloté par le processus parent via un tube de communication inter-processus (**IPC Pipe**). Si le worker dépasse son timeout ou crashe, le parent le tue sans pitié (`SIGKILL`), en relance un nouveau automatiquement, et renvoie une observation d'erreur explicite.

```
┌────────────────────────────────────────────────────────┐
│                   PROCESSUS PARENT                     │
│                 (Orchestrateur Agent)                  │
│                                                        │
│   runner = SandboxRunner(config, tools_namespace)      │
│   result = runner.execute("code...")                   │
└──────────────────────────┬─────────────────────────────┘
                           │ IPC Pipe (duplex=True)
                           │ parent_conn.send({"cmd": "EXECUTE", "code": ...})
                           ▼
┌────────────────────────────────────────────────────────┐
│                   PROCESSUS ENFANT                     │
│              (_worker_entrypoint / Worker)             │
│                                                        │
│  worker_globals = {                                    │
│      "final_answer": final_answer_callable,            │
│      "tools": tools_namespace,                         │
│      "variables_agent": ... (persistantes)             │
│  }                                                     │
│                                                        │
│  Capture stdout / stderr (io.StringIO)                 │
│  exec(compiled_code, worker_globals)                   │
└────────────────────────────────────────────────────────┘
```

---

## 2. Le modèle `ExecutionResult` (`models_private.py`)

Comme nous avons séparé nos modèles internes dans [`src/models/models_private.py`](file:///home/marberge/42/projects/agent_smith/src/models/models_private.py) pour laisser [`models_public.py`](file:///home/marberge/42/projects/agent_smith/src/models/models_public.py) strictement identique à celui de la moulinette, voici la définition de notre contrat de sortie d'exécution :

```python
class ExecutionResult(BaseModel):
    stdout: str = Field(default="")
    stderr: str = Field(default="")
    output: str = Field(default="")
    success: bool = Field(default=True)
    is_final_answer: bool = Field(default=False)
    final_answer_value: Optional[str] = Field(default=None)
    truncated: bool = Field(default=False)
    execution_time_ms: float = Field(default=0.0)
    error: Optional[str] = Field(default=None)
```

### Rôle de chaque champ :
* **`stdout`** : Les impressions console classiques (`print(...)`) générées par le code.
* **`stderr`** : Les messages d'erreurs ou logs écrits sur la sortie d'erreur standard (`sys.stderr`).
* **`output`** : La synthèse textuelle complète formatée pour être renvoyée au LLM comme **Observation**. Elle concatène proprement le `stdout`, le `[stderr]` et les éventuels `[error]`.
* **`success`** : Booléen valant `True` si le code s'est exécuté sans exception non gérée, `False` en cas d'erreur syntaxique, runtime ou timeout.
* **`is_final_answer`** : Vaut `True` uniquement si le code a appelé la fonction native `final_answer(solution)`. C'est le signal qui indique à l'agent loop de s'arrêter.
* **`final_answer_value`** : La chaîne passée en paramètre de `final_answer(...)` (ex: le code Python résolu pour MBPP ou le git diff pour SWE-bench).
* **`truncated`** : Vaut `True` si l'output total a dépassé 4 000 caractères et a été raccourci.
* **`execution_time_ms`** : Temps réel d'exécution écoulé (wall-clock time) en millisecondes.
* **`error`** : Le message d'erreur ou le traceback formaté si `success == False`.

---

## 3. Architecture IPC & Processus Persistant

Pour instancier ce worker persistant sous Linux, nous utilisons :
```python
self._mp_context = multiprocessing.get_context("fork")
parent_conn, child_conn = self._mp_context.Pipe(duplex=True)
```

### Pourquoi `multiprocessing.get_context("fork")` ?
1. **Zéro coût de démarrage** : Sous Linux, le `fork` clone instantanément la mémoire du processus sans devoir réimporter tout Python et les dépendances (démarrage en < 1 milliseconde).
2. **Transmission transparente des outils** : Toutes les fonctions et closures définies dans `tools_namespace` sont directement héritées par l'enfant au moment du fork, évitant les erreurs de sérialisation `pickle` sur les objets complexes.
3. **Sur le Pipe IPC**, nous ne faisons transiter que des types simples et légers :
   - Du parent vers l'enfant : des chaînes de code (`str`) et des commandes simples (`dict`).
   - De l'enfant vers le parent : des dictionnaires de résultats contenant du texte et des booléens.

---

## 4. Explication Pas à Pas du Code

### 4.1. `_execute_code_in_worker()` : L'exécution et capture locale

Cette fonction s'exécute **à l'intérieur du processus enfant**.

```python
def _execute_code_in_worker(
    code: str,
    worker_globals: dict[str, Any],
) -> dict[str, Any]:
```

1. **Redirection des flux** :
   ```python
   stdout_buf = io.StringIO()
   stderr_buf = io.StringIO()
   with contextlib.redirect_stdout(stdout_buf):
       with contextlib.redirect_stderr(stderr_buf):
           exec(compiled_code, worker_globals)
   ```
   Nous interceptons tout ce qui s'affiche via `print()` ou `sys.stderr.write()` dans des tampons mémoire `io.StringIO` indépendants.

2. **Compilation préalable** :
   ```python
   compiled_code = compile(code, "<sandbox>", "exec")
   ```
   Compiler le code avant de l'exécuter permet de capturer immédiatement les erreurs de syntaxe (`SyntaxError`) avec le nom de fichier virtuel `"<sandbox>"`.

3. **Interception chirurgicale des exceptions** :
   * **`except FinalAnswerSignal as signal:`** : L'agent a appelé `final_answer(answer)`. L'exécution s'interrompt normalement, nous marquons `is_final_answer = True` et stockons `signal.answer`. Pour nous, c'est un **succès** d'exécution.
   * **`except SystemExit as exc:`** : Si le code exécute `sys.exit(0)`, nous évitons que le worker ne meure silencieusement. Nous capturons le code de retour et marquons `success = False`.
   * **`except KeyboardInterrupt:`** : Nous relançons immédiatement l'exception (`raise`) pour que si l'utilisateur presse `Ctrl+C` dans le terminal, le signal ne soit pas étouffé.
   * **`except BaseException:`** : Capture toute autre exception Python et génère un traceback lisible via `traceback.format_exc()`.

4. **Composition du texte d'output** :
   Les parties `stdout`, `[stderr]` et `[error]` sont fusionnées proprement pour former un retour clair et contextualisé pour le LLM.

---

### 4.2. `_worker_entrypoint()` : La boucle événementielle du processus enfant

C'est la fonction cible (`target`) du processus enfant.

```python
def _worker_entrypoint(
    conn: multiprocessing.connection.Connection,
    config: SandboxConfig,
    tools_namespace: dict[str, Any] | None,
) -> None:
```

1. **Définition de `final_answer`** :
   ```python
   def final_answer(answer: Any) -> None:
       raise FinalAnswerSignal(str(answer))
   ```
   Cette fonction est injectée directement dans `worker_globals`. Quand le code l'invoque, elle lève le signal interne.

2. **Initialisation de l'espace de noms persistant** :
   ```python
   worker_globals: dict[str, Any] = {
       "__name__": "__main__",
       "__doc__": None,
       "final_answer": final_answer,
   }
   if tools_namespace:
       for name, tool in tools_namespace.items():
           worker_globals[name] = tool
   ```
   Toutes les fonctions d'outils (ex: `run_tests`, `read_file`) deviennent directement accessibles comme des fonctions globales dans le code de l'agent.

3. **Boucle d'écoute infinie (`while True`)** :
   Le worker se met en sommeil en attendant un message sur le pipe (`conn.poll(None)` / `conn.recv()`) :
   * **`"EXECUTE"`** : Exécute le code via `_execute_code_in_worker()` et renvoie le résultat via `conn.send({"status": "OK", "data": res})`. `worker_globals` n'est pas réinitialisé : **les variables persistent pour le prochain message** !
   * **`"RESET"`** : Réinitialise `worker_globals` à son état initial propre et confirme au parent.
   * **`"SHUTDOWN"`** : Sort de la boucle et termine proprement le processus.

---

### 4.3. `SandboxRunner` : Le contrôleur côté processus parent

C'est la classe principale manipulée par l'orchestrateur.

#### `__init__(self, config, tools_namespace=None)`
Instancie la configuration, sauvegarde les outils, et appelle immédiatement `_start_worker()` pour lancer le processus enfant.

#### `_start_worker(self)`
```python
parent_conn, child_conn = self._mp_context.Pipe(duplex=True)
process = self._mp_context.Process(
    target=_worker_entrypoint, args=(child_conn, ...)
)
process.start()
child_conn.close()
```
> [!TIP]
> **Règle d'or Unix :** Le parent doit impérativement fermer sa propre copie de `child_conn` (`child_conn.close()`). Si le parent gardait ce descripteur de fichier ouvert, en cas de crash brutal du processus enfant, le parent ne recevrait jamais le signal `EOF` sur le pipe et risquerait de rester bloqué indéfiniment.

#### `_terminate_worker(self)`
Ferme le pipe et arrête le processus worker :
1. Tente un arrêt propre via `terminate()` (`SIGTERM`) avec un délai d'attente de 1 seconde.
2. Si le worker refuse de s'arrêter (par exemple s'il est bloqué dans une boucle en C), déclenche un `kill()` immédiat (`SIGKILL`).

#### `_truncate_output(self, text, max_chars=4000)`
Vérifie la longueur du texte produit :
* Si $\le 4000$ caractères : renvoie le texte tel quel et `False`.
* Si $> 4000$ caractères : découpe à 4 000 caractères et ajoute explicitement la mention :
  `"\n... [Tool output was truncated due to size limits: showing first 4000 of X characters] ..."`
  Ceci empêche que la fenêtre de contexte du LLM ne soit saturée par des sorties de logs gigantesques, tout en l'avertissant clairement que la sortie a été tronquée (exigence Section V.1.2 du sujet).

#### `execute(self, code: str) -> ExecutionResult`
C'est la méthode maîtresse qui gère la communication et la résilience :

1. **Auto-démarrage si worker inactif** : Si le worker précédent a été tué ou n'est plus vivant, `_start_worker()` est appelé automatiquement.
2. **Envoi de l'instruction** :
   ```python
   self._parent_conn.send({"cmd": "EXECUTE", "code": code})
   ```
3. **Surveillance du Timeout** :
   ```python
   has_data = self._parent_conn.poll(timeout)
   if not has_data:
       self._terminate_worker()  # Tue le worker bloqué
       self._start_worker()  # Recrée un worker neuf
       return ExecutionResult(
           ..., error=f"Execution hit the timeout ({timeout}s)..."
       )
   ```
   Si le code met plus de `max_execution_time_seconds` à répondre, le parent n'attend pas : il tue le worker, en relance un propre, et renvoie un résultat d'échec propre.
4. **Surveillance des Crashs (Pipe cassé)** :
   ```python
   try:
       response = self._parent_conn.recv()
   except (EOFError, BrokenPipeError):
       self._terminate_worker()
       self._start_worker()
       return ExecutionResult(
           ..., error="Sandbox worker process terminated unexpectedly..."
       )
   ```
   Si le worker crashe brutalement (ex: tué par le système pour dépassement de mémoire RAM), l'exception `EOFError` est interceptée, un nouveau worker est relancé, et une erreur claire est retournée.
5. **Formatage final** :
   Le texte de sortie est tronqué si besoin via `_truncate_output()` et le résultat est encapsulé dans l'objet Pydantic `ExecutionResult`.

#### `reset()` & `close()`
* `reset()` envoie la commande `"RESET"` pour nettoyer la mémoire du worker sans avoir à détruire le processus système.
* `close()` envoie `"SHUTDOWN"` puis force le nettoyage des ressources.
* Support du protocole context manager (`with SandboxRunner(...) as runner:`).

---

## 5. Gestion des Cas Critiques & Sécurité

### Boucles infinies & Timeouts
* **Scénario** : L'agent écrit `while True: pass` ou un calcul trop lourd.
* **Comportement** : Le parent bloque sur `poll(timeout)`. Dès que le délai configuré (ex: 30s ou 5s) est atteint, le parent force l'arrêt du worker via `SIGKILL`. L'orchestrateur ne gèle jamais.

### Crashs mémoires / SIGSEGV & Auto-Recovery
* **Scénario** : Le code alloue un tableau géant qui dépasse la limite mémoire (`rlimit`) ou déclenche un signal d'arrêt noyau.
* **Comportement** : Le processus worker meurt. Le pipe se brise immédiatement. Le parent intercepte `EOFError`, détruit les descripteurs orphelins, instancie un nouveau worker, et rapporte l'incident sans faire échouer l'application globale.

### Pourquoi `FinalAnswerSignal` hérite de `BaseException`
En Python, la hiérarchie des exceptions est la suivante :
```text
BaseException
 ├── KeyboardInterrupt
 ├── SystemExit
 ├── FinalAnswerSignal  <-- Notre signal
 └── Exception
      ├── ValueError
      ├── TypeError
      └── ... (toutes les exceptions standard)
```
Si un développeur ou un LLM génère du code contenant :
```python
try:
    final_answer("ma solution")
except Exception as e:
    print("Erreur ignorée :", e)
```
Comme `FinalAnswerSignal` n'hérite pas d'`Exception`, le bloc `except Exception` **ne peut pas l'attraper**. Le signal remonte directement au moteur d'exécution de la sandbox, garantissant que l'agent ne reste pas coincé dans sa boucle.

---

## 6. Validation & Tests Unitaires

Tous ces comportements sont validés et testés unitairement dans [`tests/test_sandbox_core.py`](file:///home/marberge/42/projects/agent_smith/tests/test_sandbox_core.py) :

| Nom du Test | Comportement vérifié |
| :--- | :--- |
| `test_basic_execution` | Exécution standard d'un print et capture de `stdout`. |
| `test_state_persistence_across_executions` | Persistance des variables et fonctions entre deux appels successifs à `execute()`. |
| `test_final_answer_interception` | Interception de `final_answer(solution)` et positionnement de `is_final_answer=True`. |
| `test_custom_tools_namespace` | Appel fluide d'une fonction injectée dans `tools_namespace`. |
| `test_output_truncation` | Tronquage à 4 000 caractères avec avertissement explicite. |
| `test_execution_timeout_and_worker_recovery` | Tuerie sur timeout d'une boucle infinie et vérification que le worker relancé fonctionne immédiatement. |
| `test_error_traceback_capture` | Formatage lisible des erreurs (ex: `ZeroDivisionError`). |
| `test_reset_clears_namespace` | Nettoyage des variables utilisateur avec `runner.reset()`. |

La suite de tests s'exécute avec succès via :
```bash
pytest tests/test_sandbox_core.py
```
*(39 tests passés au total avec 100% de succès et conformité mypy / flake8)*.

