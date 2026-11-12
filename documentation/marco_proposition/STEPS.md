# Les Grandes Étapes du Projet Agent Smith

Ce document synthétise les grandes étapes de conception et de réalisation du projet **Agent Smith** (42). Il détaille l'enchaînement logique des développements nécessaires pour construire un **Code Agent** autonome, sécurisé, conforme au protocole **MCP** et capable de réussir les benchmarks **MBPP** et **SWE-bench**.

---

## 🎯 Rappel de l'objectif

Contrairement à un simple chatbot ou à un système d'appel d'outils par JSON (*function calling* natif), **Agent Smith** est un **Code Agent**. Il résout des problèmes de code en programmant lui-même en Python dans une boucle fermée :
$$\text{Thought} \longrightarrow \text{Code} \longrightarrow \text{Observation}$$

L'agent raisonne, écrit du code Python qui appelle des outils (recherche de symboles, lecture de fichiers, exécution de tests), exécute ce code dans un **bac à sable (Sandbox)** sécurisé, analyse le retour d'exécution et itère jusqu'à converger vers une solution validée.

---

## 🗺️ Vue d'ensemble de la feuille de route

Le projet s'articule autour de **7 étapes majeures**, conçues pour avancer du plus bas niveau et du plus contrôlable vers le plus complexe et autonome :

```
┌─────────────────────────────────────────────────────────────┐
│ Étape 0 : Socle technique, environnement & contrats Pydantic│
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Étape 1 : Le Bac à sable sécurisé (Sandbox) & mode REPL     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Étape 2 : Le protocole MCP (Serveurs & Outils)              │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Étape 3 : Abstraction LLM & Gestion Multi-Tokens / Quotas   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Étape 4 : L'Orchestrateur & Agent MBPP (Algorithmique)      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Étape 5 : L'Agent SWE-bench & Intégration Docker (Bugs réels)│
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Étape 6 : Campagne de Benchmark, Documentation & Soutenance │
└─────────────────────────────────────────────────────────────┘
```

---

## Étape 0 : Socle technique, environnement & modèles Pydantic

Avant d'écrire la moindre ligne d'orchestration, il faut établir les fondations techniques imposées par le sujet :
1. **Environnement** : Configuration sous **Python 3.10** et initialisation stricte des dépendances avec **`uv`** (`uv.lock`, `pyproject.toml`).
2. **Modèles de données (Pydantic v2)** : Le sujet impose des structures de données très précises pour les échanges et la moulinette :
   - `SandboxConfig` : whitelist d'imports, répertoires autorisés, timeout, limite RAM.
   - `MBPPTaskInput` & `SWEBenchTaskInput` : chargement standardisé des tâches.
   - `StepMetrics` & `SolutionOutput` : journalisation pas à pas obligatoire (tokens d'entrée/sortie, temps d'API, prompts bruts, codes injectés, retours sandbox, retries).
3. **Configuration & Secrets** : Mise en place d'un système de chargement via `.env` et variables d'environnement (interdiction absolue de commiter une clé API).

---

## Étape 1 : Le Bac à sable sécurisé (Sandbox) & REPL interactif

L'exécution de code Python généré dynamiquement par une IA représente un risque d'escalade de privilèges critique. La sandbox est la frontière étanche du système.

1. **Règles de sécurité strictes (Bibliothèque standard uniquement !)** :
   *Interdiction formelle d'utiliser des packages tiers comme `RestrictedPython`.*
   - **Contrôle des imports** : Whitelist stricte (`authorized_imports` : `math`, `collections`, `itertools`, `re`, `json`, etc. avec support de `.*`).
   - **Isolation du système de fichiers** : Whitelist de chemins autorisés (`allowed_directories` : ex `/testbed`, `/tmp/agent`). Tout accès en dehors doit échouer.
   - **Blocage réseau absolu** : Empêcher toute ouverture de socket ou communication entrante/sortante depuis le code utilisateur.
   - **Builtins assainis** : Redéfinition ou suppression des builtins dangereux (`eval`, `exec`, `open` non sandboxé, `__import__`, etc.).
   - **Limites de ressources** : Application d'un timeout strict (`signal.SIGALRM` ou surveillance de sous-processus) et plafonnement mémoire (`resource.setrlimit`).
2. **Architecture d'exécution** :
   - Choix de l'isolation : exécution dans un sous-processus dédié (`multiprocessing` ou `subprocess`) pour permettre de tuer net (`SIGTERM`/`SIGKILL`) tout code qui boucle à l'infini sans corrompre le processus parent.
   - Gestion des flux : capture propre de `stdout` et `stderr`.
   - Propagation des exceptions critiques : `KeyboardInterrupt` et `SystemExit` ne doivent jamais être masqués.
3. **Fonction injectée `final_answer(solution)`** :
   - Fonction résidant dans la sandbox (et non sur le serveur MCP).
   - Permet à l'agent de marquer la fin de son travail et de transmettre la solution finale à l'orchestrateur.
4. **Interface CLI & Mode REPL** :
   - `uv run sandbox` : lance un REPL interactif simulant l'environnement de l'agent.
   - `uv run sandbox sandbox_template.json` : prend en compte une configuration JSON.

---

## Étape 2 : Le protocole MCP (Serveurs & Outils)

Le protocole **Model Context Protocol** (MCP) standardise l'exposition d'outils et de contextes aux modèles.

1. **Serveurs MCP dédiés** :
   - Implémentation conforme aux spécifications MCP via transport **`stdio`** et **`streamable HTTP`**.
   - Fichiers obligatoires situés à la racine : `mcp_tools_mbpp.py` et `mcp_tools_swebench.py`.
2. **Outils obligatoires pour SWE-bench** :
   - *Fichiers* : `read_file(filepath, start_line, end_line)` (numérotation des lignes style `cat -n`), `edit_file(filepath, old_str, new_str)`, `list_files(directory, pattern)`.
   - *Recherche de code* : `search_code(pattern, file_pattern)`, `search_function_or_class_definition_in_code(name)`, `find_references(name, filepath, line)`.
   - *Exécution* : `run_tests()`, `get_patch()`, `run_command(command, workdir)`.
   - *Variable d'environnement* : Prise en charge stricte de `TESTBED_PATH` pour situer la racine du dépôt cible.
3. **Outils pour MBPP** :
   - `run_tests(code, test_list)` : exécute le code candidat face aux assertions de tests fournies et renvoie un JSON `{success: bool, output: str}`.
4. **Manuel dynamique (Sandbox Manual)** :
   - Le système doit interroger le serveur MCP connecté (introspection des outils disponibles) et générer dynamiquement la documentation textuelle des fonctions pour l'injecter dans le prompt de l'agent. Si le serveur change, le prompt s'adapte sans redémarrage.

---

## Étape 3 : Abstraction LLM & Gestion Multi-Tokens / Quotas

Pour supporter l'évaluation sur des tiers 100% gratuits et résister aux aléas réseau et rate limits :
1. **Couche d'abstraction Providers** :
   - Interface commune capable de cibler OpenRouter, Groq, Google AI Studio (Gemini), Mistral, Together AI, etc.
   - Paramétrage des requêtes : température, token limits, et surtout `stop_sequences` (ex: `<end_code>`, `Observation:`) pour empêcher le LLM d'inventer lui-même les retours de la sandbox.
2. **Gestion multi-tokens & rotation** :
   - Chargement de listes de clés API par fournisseur.
   - Détection des erreurs 429 (*Rate Limit Exceeded*) et quotas épuisés avec bascule transparente vers la clé suivante (Round-Robin ou Pool avec cooldown).
   - Mécanisme de repli (*fallback*) vers un provider secondaire si un fournisseur s'arrête complètement.
3. **Extraction robuste de code** :
   - Parser capable d'extraire le code Python généré (blocs markdown ````python ... ````).
   - Capacité de traduire d'autres formats fréquents (XML Anthropic, JSON Hermes, ReAct) en appels Python équivalents pour que la sandbox reste agnostique.
4. **Feedback explicite au modèle** :
   - Si le code est absent, malformé, tronqué ou en timeout, la sandbox doit renvoyer un message d'erreur clair et constructif dans l'observation pour guider l'itération suivante du LLM.

---

## Étape 4 : L'Agent MBPP & Validation de la première boucle

MBPP est le banc d'essai idéal pour valider toute la mécanique agentique avant d'aborder la complexité de Docker.

1. **CLI `agent_mbpp`** :
   - Module exécutable via `uv run python -m agent_mbpp --task-file <PATH> --output <PATH> --model-name <MODEL> --provider-url <URL>`.
2. **Boucle d'orchestration MBPP** :
   - Initialisation avec la consigne de tâche (`task_definition`, signature de fonction).
   - Itération : Thought → Code (`run_tests`) → Observation.
   - Condition de sortie : appel de `final_answer(code)` dès que tous les tests passent, ou épuisement du budget d'itérations.
3. **Respect des limites drastiques de MBPP** :
   - **Max 10 itérations**.
   - **Max 6 000 input tokens**.
   - **Max 1 500 output tokens**.
   - **Timeout global : 120 secondes**.
   - Objectif d'évaluation : **4 tâches réussies sur 5**.

---

## Étape 5 : L'Agent SWE-bench & Intégration Docker

SWE-bench confronte l'agent à de vrais dépôts open source conteneurisés (Django, SymPy, xarray, Sphinx...).

1. **Architecture Docker** :
   - Gestion des conteneurs basés sur les images officielles SWE-bench (`swebench/sweb.eval.x86_64...`).
   - Deux approches possibles : soit la sandbox s'exécute dans le conteneur, soit elle tourne sur l'hôte et les outils MCP font le pont avec `docker exec`.
   - **Nettoyage impératif** : nettoyage rigoureux des conteneurs après exécution, y compris en cas de `SIGTERM`/`SIGKILL`.
2. **CLI `agent_swebench`** :
   - Commande : `uv run python -m agent_swebench --task-file ... --output ...`.
3. **Stratégie de résolution** :
   - Exploration du repo (recherche par grep, localisation des définitions de classes/fonctions).
   - Reproduction du bug via l'exécution du script de test (`run_tests()`).
   - Correction ciblée avec `edit_file`.
   - Vérification de non-régression et extraction du git diff (`get_patch()` via `git -c core.fileMode=false diff`).
   - Clôture avec `final_answer(patch)`.
4. **Respect des limites SWE-bench** :
   - **Max 30 itérations**.
   - **Max 300 000 input tokens**.
   - **Max 10 000 output tokens**.
   - **Timeout global : 900 secondes (15 min)**.
   - Objectif d'évaluation : **2 tâches réussies sur 3**.

---

## Étape 6 : Campagne de Benchmark, Documentation & Soutenance

1. **Benchmark comparatif (`BENCHMARK_REPORT.md`)** :
   - Évaluer au moins **5 modèles** différents sur au moins **2 providers distincts** sur les **3 mêmes tâches SWE-bench**.
   - Mesurer les métriques imposées : Pass/Fail, itérations, tokens in/out, temps wall-clock, latence moyenne, retries.
   - Analyser au moins 2 métriques intermédiaires (étape du premier touché de fichier, régression des tests, discipline de soumission).
   - Réaliser une **étude d'ablation** (mesurer l'impact d'un changement dans le prompt ou le set d'outils).
   - Fournir tous les fichiers `solution.json` bruts justifiant les résultats.
2. **README.md réglementaire** :
   - En anglais, respectant la phrase d'en-tête 42 obligatoire.
   - Explication détaillée de l'architecture, de la sandbox, de la boucle agent et des outils.
3. **Préparation à la soutenance orale** :
   - Maîtrise parfaite de la base de code pour réussir l'épreuve de **live-coding** (modifier un comportement de l'agent en 2 à 5 minutes chrono devant les évaluateurs).
