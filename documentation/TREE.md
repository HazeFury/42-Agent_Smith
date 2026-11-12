# Architecture du Projet — Agent Smith

Ce document présente la structure d'arborescence recommandée pour le projet **Agent Smith**, détaille le rôle de chaque composant et justifie les choix architecturaux au regard des contraintes techniques et des exigences de l'évaluation 42.

---

## 🌳 Arborescence du Projet

```text
agent_smith/
├── .env.example                     # Modèle des variables d'environnement (clés API)
├── .gitignore                       # Exclusion des caches, .env, venv, conteneurs
├── pyproject.toml                   # Métadonnées du projet, dépendances uv et scripts CLI
├── uv.lock                          # Verrouillage déterministe des dépendances
├── README.md                        # Documentation officielle (en anglais, norme 42)
├── BENCHMARK_REPORT.md              # Rapport officiel de comparaison des modèles
├── sandbox_template.json            # Configuration par défaut du bac à sable (JSON)
│
├── agent_mbpp.py                    # Point d'entrée CLI pour MBPP (python -m agent_mbpp)
├── agent_swebench.py                # Point d'entrée CLI pour SWE-bench (python -m agent_swebench)
├── mcp_tools_mbpp.py                # Serveur MCP pour MBPP (imposé à la racine)
├── mcp_tools_swebench.py            # Serveur MCP pour SWE-bench (imposé à la racine)
│
├── documentation/                   # Documentation de travail et de conception
│   ├── NOTIONS.md                   # Glossaire et concepts clés (IA, MCP, Sandboxing)
│   ├── PLANNING.md                  # Répartition Marco & Steph et calendrier
│   ├── STEPS.md                     # Les 6 étapes clés du projet
│   └── TREE.md                      # Le présent document d'architecture
│
├── evaluations/                     # Traces et sorties des évaluations (moulinette)
│   └── .gitkeep
│
├── tests/                           # Tests unitaires et d'intégration
│   ├── test_sandbox_security.py     # Tests d'intrusion de la sandbox (100% requis)
│   ├── test_llm_rotation.py         # Tests de rotation de clés et tolérance aux pannes
│   ├── test_code_extractor.py       # Tests d'extraction de code (Python, XML, JSON)
│   ├── test_mcp_tools.py            # Tests unitaires des outils de fichiers et recherche
│   └── test_mbpp_loop.py            # Test d'intégration de la boucle ReAct
│
└── src/                             # Code source modulaire du projet
    ├── __init__.py
    │
    ├── models/                      # Modèles de données Pydantic v2 (contrats stricts)
    │   ├── __init__.py
    │   ├── config.py                # SandboxConfig (allowlists, timeouts, RAM)
    │   ├── tasks.py                 # MBPPTaskInput, SWEBenchTaskInput
    │   └── metrics.py               # StepMetrics, SolutionOutput
    │
    ├── sandbox/                     # Moteur d'exécution sécurisé et isolé
    │   ├── __init__.py
    │   ├── core.py                  # Exécution du code dans un sous-processus isolé
    │   ├── security.py              # Analyse statique AST, filtrage des imports
    │   ├── builtins_guard.py        # Whitelist et assainissement des builtins Python
    │   ├── fs_guard.py              # Contrôle d'accès au système de fichiers (paths)
    │   ├── limits.py                # Gestion des timeouts et de la mémoire (setrlimit)
    │   └── cli.py                   # Mode REPL interactif (uv run sandbox)
    │
    ├── mcp/                         # Client et bridge Model Context Protocol
    │   ├── __init__.py
    │   ├── client.py                # Client MCP (connexions stdio et HTTP)
    │   ├── dynamic_manual.py        # Génération dynamique du manuel d'outils
    │   └── bridge.py                # Injection des outils MCP comme fonctions Python
    │
    ├── llm/                         # Abstraction des LLM et gestion des quotas
    │   ├── __init__.py
    │   ├── client.py                # Client unifié (OpenRouter, Groq, Gemini...)
    │   ├── key_manager.py           # Multi-token pool, détection 429 & rotation
    │   ├── token_tracker.py         # Comptage précis des tokens et latences
    │   └── providers/               # Adaptateurs spécifiques par provider
    │       ├── __init__.py
    │       ├── base.py
    │       ├── openrouter.py
    │       ├── groq.py
    │       └── gemini.py
    │
    ├── agent/                       # Orchestration de la boucle cognitive
    │   ├── __init__.py
    │   ├── loop.py                  # Boucle ReAct : Thought → Code → Observation
    │   ├── prompt_builder.py        # Assemblage du prompt système et consignes
    │   ├── code_extractor.py        # Extraction de code et conversion de formats
    │   ├── mbpp_agent.py            # Logique spécialisée MBPP
    │   └── swebench_agent.py        # Logique spécialisée SWE-bench
    │
    └── tools/                       # Implémentation concrète des outils métier
        ├── __init__.py
        ├── file_tools.py            # read_file (cat -n), edit_file, list_files
        ├── search_tools.py          # search_code, search_definitions, find_references
        ├── execution_tools.py       # run_tests, run_command, get_patch
        └── docker_manager.py        # Gestion des conteneurs SWE-bench & nettoyage
```

---

## 🔍 Rôle Détaillé des Fichiers et Dossiers

### 1. Fichiers de configuration & racine
* **`pyproject.toml`** : Configure le projet avec Python 3.10 et les dépendances `uv`. Définit le script d'entrée console `[project.scripts] sandbox = "src.sandbox.cli:main"` pour que la commande `uv run sandbox` fonctionne directement.
* **`mcp_tools_mbpp.py` & `mcp_tools_swebench.py`** : Emplacement **strictement imposé par le sujet à la racine**. Ils instancient et démarrent les serveurs MCP (stdio/HTTP) en exposant les outils requis.
* **`agent_mbpp.py` & `agent_swebench.py`** : Points d'entrée légers à la racine permettant d'exécuter `uv run python -m agent_mbpp ...` et `uv run python -m agent_swebench ...` tels qu'exigés par la moulinette.
* **`sandbox_template.json`** : Gabarit de configuration par défaut (whitelist d'imports, dossiers autorisés, timeout) utilisé pour lancer la sandbox.
* **`BENCHMARK_REPORT.md`** : Rapport de benchmark imposé comparant 5 modèles sur 2 providers et 3 tâches SWE-bench.
* **`README.md`** : Documentation principale du projet en anglais respectant l'en-tête 42.

### 2. Le package `src/models/`
Centralise tous les contrats de données Pydantic imposés par le sujet :
* **`config.py`** : Contient `SandboxConfig` (whitelist d'imports avec support de `.*`, `allowed_directories`, timeout, max RAM).
* **`tasks.py`** : Modèles d'entrée `MBPPTaskInput` et `SWEBenchTaskInput`.
* **`metrics.py`** : Modèles `StepMetrics` et `SolutionOutput` pour garantir la conformité exacte du fichier `solution.json`.

### 3. Le package `src/sandbox/`
Dédié à l'isolation et à la sécurité d'exécution du code Python :
* **`core.py`** : Lance le code dans un sous-processus isolé, capture `stdout`/`stderr` et gère le retour.
* **`security.py`** : Parse le code via `ast.parse` avant exécution pour rejeter tout import non autorisé ou tentative de traversée d'objets (`__subclasses__`, `__globals__`).
* **`builtins_guard.py`** : Fournit un dictionnaire `__builtins__` sécurisé où `eval`, `exec` et `__import__` dangereux sont supprimés ou remplacés par un importeur filtré.
* **`fs_guard.py`** : Version sécurisée de `open()` qui résout les chemins réels et bloque tout accès hors des dossiers de `allowed_directories`.
* **`limits.py`** : Applique les quotas mémoire Linux (`resource.setrlimit`) et les timeouts stricts.
* **`cli.py`** : Implémente le mode REPL interactif (`uv run sandbox`).

### 4. Le package `src/mcp/`
Gère la communication avec le protocole Model Context Protocol :
* **`client.py`** : Client capable d'établir des sessions MCP via `stdio` ou `streamable HTTP`.
* **`dynamic_manual.py`** : Interroge le serveur MCP connecté pour inspecter la liste des outils, leurs paramètres et descriptions afin de formater le manuel textuel injecté dans le prompt de l'agent.
* **`bridge.py`** : Fait le pont en injectant dans l'espace de noms de la sandbox des fonctions Python correspondant aux outils MCP.

### 5. Le package `src/llm/`
Gère les appels aux modèles distants et la résilience :
* **`client.py`** : Façade d'envoi des requêtes LLM unifiée.
* **`key_manager.py`** : Pool de clés d'API par fournisseur, détection des codes HTTP 429 et rotation automatique transparente.
* **`token_tracker.py`** : Mesure du temps d'API (wall-clock ms), décompte précis des tokens d'entrée et de sortie.
* **`providers/`** : Implémentations légères adaptées aux spécificités de chaque API (Groq, OpenRouter, Gemini).

### 6. Le package `src/agent/`
Le cœur de l'orchestrateur (interdiction des frameworks externes comme LangChain) :
* **`loop.py`** : La boucle maîtresse ReAct (`Thought → Code → Observation`). Elle gère le compteur d'itérations, les quotas de tokens, la détection de `final_answer` et la compilation du `SolutionOutput`.
* **`prompt_builder.py`** : Génère le prompt système combinant les consignes de formatage, les exemples de raisonnement et le manuel des outils.
* **`code_extractor.py`** : Extrait proprement le code Python des blocs ````python ... ```` et sait convertir les formats alternatifs (XML Anthropic, JSON Hermes).
* **`mbpp_agent.py` & `swebench_agent.py`** : Contrôleurs spécialisés pour charger les tâches, piloter la boucle et formater la solution.

### 7. Le package `src/tools/`
L'implémentation opérationnelle des outils appelés par le serveur MCP SWE-bench :
* **`file_tools.py`** : `read_file` avec numérotation de lignes (`cat -n`), `edit_file`, `list_files`.
* **`search_tools.py`** : Recherche grep (`search_code`), repérage de définitions de classes/fonctions et localisation de références.
* **`execution_tools.py`** : `run_tests()`, `run_command()`, `get_patch()` (`git -c core.fileMode=false diff`).
* **`docker_manager.py`** : Gestion des conteneurs Docker (démarrage, montage de volume, `TESTBED_PATH`, destruction garantie avec capture de signaux `SIGTERM`).

---

## ⚖️ Justification des Choix d'Architecture

### 1. Conformité stricte aux exigences de la moulinette
Le sujet impose des commandes très spécifiques :
* `uv run sandbox` : Rendu possible grâce au point d'entrée `[project.scripts]` de `pyproject.toml` qui pointe vers `src/sandbox/cli.py`.
* `python -m agent_mbpp` et `python -m agent_swebench` : Rendu possible par les modules légers placés à la racine (`agent_mbpp.py` et `agent_swebench.py`) qui importent et exécutent la logique de `src/agent/`.
* `mcp_tools_mbpp.py` et `mcp_tools_swebench.py` : Placés directement à la racine comme explicitement exigé dans les sections V.2.4 et V.4 du sujet.

### 2. Découplage fort (Principe de Responsabilité Unique)
* **La Sandbox ne connaît pas le LLM** : Le bac à sable ne sait pas d'où vient le code. Il reçoit du code, l'analyse, l'exécute sous contraintes et renvoie une sortie texte. Cela permet de tester la sandbox unitairement de façon exhaustive sans dépenser le moindre token.
* **Les Outils MCP sont autonomes** : Ils peuvent être testés indépendamment de l'agent (conformément à ce qui est testé lors de la revue d'évaluation).
* **L'Orchestrateur est agnostique du fournisseur** : Passer d'OpenRouter à Groq ou Gemini ne demande aucune modification de la boucle agent ni des prompts.

### 3. Sécurité sans dépendance externe
Pour respecter l'interdiction de `RestrictedPython` :
* La combinaison d'un **parseur AST statique** (`security.py`) et d'un **environnement d'exécution assaini dans un sous-processus** (`core.py`, `limits.py`) offre une double barrière étanche.
* L'isolation par sous-processus (`multiprocessing` ou `subprocess`) protège contre les blocages mémoire et les boucles infinies en permettant un arrêt net par signal POSIX (`SIGKILL`).

### 4. Lisibilité pour la soutenance (Live-Coding en 2-5 minutes)
Pendant la peer-review, les correcteurs demandent d'effectuer une petite modification en live. Grâce à ce découpage :
* Modifier le comportement d'un outil $\rightarrow$ fichier unique dans `src/tools/`.
* Modifier une règle de sécurité $\rightarrow$ `src/sandbox/security.py` ou `builtins_guard.py`.
* Modifier le prompt ou le formatage $\rightarrow$ `src/agent/prompt_builder.py`.
* Aucun fichier "fourre-tout" monolithique de 1 000 lignes : chaque fichier a un rôle clair, ce qui évite de paniquer sous le chrono de 5 minutes.
