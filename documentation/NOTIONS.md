# Glossaire des Notions Clés — Agent Smith

Ce document recense l'ensemble des notions, acronymes, concepts théoriques et mots-clés techniques indispensables pour comprendre, concevoir et soutenir le projet **Agent Smith**.

---

## Sommaire

1. [Table des Acronymes](#1-table-des-acronymes)
2. [Intelligence Artificielle & Ingénierie Agentique](#2-intelligence-artificielle--ingénierie-agentique)
3. [Protocole MCP (Model Context Protocol)](#3-protocole-mcp-model-context-protocol)
4. [Sécurité, Sandboxing & Systèmes](#4-sécurité-sandboxing--systèmes)
5. [Benchmarks & Évaluation de Code](#5-benchmarks--évaluation-de-code)
6. [Gestion des API LLM, Quotas & Résilience](#6-gestion-des-api-llm-quotas--résilience)
7. [Écosystème & Outillage Python Moderne](#7-écosystème--outillage-python-moderne)

---

## 1. Table des Acronymes

| Acronyme | Signification | Description synthétique |
| :--- | :--- | :--- |
| **LLM** | *Large Language Model* | Modèle de langage de grande taille entraîné sur d'immenses corpus textuels. |
| **MCP** | *Model Context Protocol* | Standard ouvert initié par Anthropic pour connecter des modèles à des outils et contextes. |
| **MBPP** | *Mostly Basic Python Problems* | Benchmark de problèmes algorithmiques Python courts créé par Google. |
| **SWE** | *Software Engineering* | Ingénierie logicielle (terme générique dans SWE-bench). |
| **ReAct** | *Reasoning + Acting* | Pattern agentique combinant raisonnement pas à pas et exécution d'actions. |
| **AST** | *Abstract Syntax Tree* | Arbre syntaxique abstrait représentant la structure grammaticale d'un code source. |
| **REPL** | *Read-Eval-Print Loop* | Environnement interactif qui lit, évalue, affiche et répète des commandes de code. |
| **CLI** | *Command Line Interface* | Interface en ligne de commande. |
| **RPM / TPM** | *Requests / Tokens Per Minute* | Mesures de quotas et de limitation de débit des fournisseurs d'API. |
| **SSE** | *Server-Sent Events* | Protocole HTTP unidirectionnel de streaming de données du serveur vers le client. |
| **JSON-RPC** | *JSON Remote Procedure Call* | Protocole d'appel de procédure distante encodé en JSON, sous-jacent à MCP. |

---

## 2. Intelligence Artificielle & Ingénierie Agentique

### Large Language Model (LLM) & Inférence
* **Inférence** : Phase d'exécution durant laquelle le modèle génère du texte en réponse à une consigne (prompt), token par token, à partir de probabilités apprises.
* **Tokens & Tokenisation** : Sous-unités de mots utilisées par les modèles (environ 1 token $\approx$ 0.75 mot ou 3-4 caractères de code).
  * *Input Tokens (Prompt Tokens)* : Nombre de tokens envoyés au modèle.
  * *Output Tokens (Completion Tokens)* : Nombre de tokens produits en réponse.
  * *Reasoning / Thinking Tokens* : Tokens internes générés par les modèles dits "de raisonnement" (ex: o1, DeepSeek-R1, QwQ). Dans ce projet, ils comptent dans le quota d'output tokens !
* **Context Window (Fenêtre de contexte)** : Quantité maximale totale de tokens qu'un modèle peut lire et conserver en mémoire lors d'un appel.

### Agent IA vs Chatbot
* **Chatbot traditionnel** : Prend une question en entrée, renvoie une réponse directe en une seule passe, sans effet de bord ni capacité d'interaction avec le monde extérieur.
* **Agent Autonome** : Entité logicielle dotée d'objectifs, capable d'observer un environnement, de raisonner, de planifier, d'agir via des outils (*tools*), d'observer le résultat et de réitérer jusqu'à atteindre son but sans intervention humaine.

### Code Agent vs JSON Tool-Calling
* **JSON Tool-Calling** : Méthode standard des API (OpenAI/Anthropic) où le modèle génère un objet JSON décrivant une fonction et ses arguments (`{"name": "read_file", "args": {"path": "main.py"}}`).
  * *Limites* : Un seul appel à la fois, pas de variables réutilisables, pas de boucles, forte latence due aux allers-retours continus avec l'API.
* **Code Agent (l'approche d'Agent Smith)** : Le modèle génère directement un **bloc de code Python exécutable**.
  * *Avantages majeurs* : L'agent peut chaîner plusieurs actions dans une seule itération, manipuler des variables d'étape en étape, faire des filtres, des conditions et des boucles de contrôle localement dans la sandbox.

### Le Pattern ReAct (Reasoning + Acting)
Boucle itérative structurée en trois temps :
1. **Thought** : Monologue intérieur où l'agent explicite ses déductions, analyse l'état courant et formule une hypothèse.
2. **Code (Action)** : Code Python généré pour interroger l'environnement ou appliquer une modification.
3. **Observation** : Sortie textuelle brute (stdout, stderr, code de retour) produite par l'exécution du code dans la sandbox.

### Stop Sequences (Séquences d'arrêt)
Paramètre d'API forçant le LLM à stopper net sa génération dès qu'une chaîne donnée apparaît (ex: `<end_code>` ou `Observation:`).
* *Pourquoi c'est vital ?* Sans stop sequence, les LLM ont tendance à "halluciner" l'observation de la sandbox (inventer la sortie d'un test qui n'a pas encore été exécuté) au lieu d'attendre la vraie exécution.

### Étude d'Ablation (Ablation Study)
Expérimentation scientifique consistant à retirer ou modifier un composant précis du système (par exemple : enlever l'outil `find_references`, changer le prompt système, ou modifier la limite d'itérations) sur un même échantillon de tâches pour mesurer scientifiquement son apport réel.

---

## 3. Protocole MCP (Model Context Protocol)

### Définition & Rôle
Créé par Anthropic en 2024, **MCP** est un protocole standardisé basé sur JSON-RPC 2.0 permettant de connecter de manière unifiée des modèles d'IA à des sources de données et des outils externes, indépendamment du modèle ou de la plateforme hôte.

### Architecture Client / Serveur
* **Serveur MCP** : Processus indépendant qui expose des capacités (outils, fichiers, commandes système).
* **Client MCP** : Composant de notre application qui se connecte au serveur, découvre ses fonctionnalités et les invoque à distance.

### Primitives MCP
* **Tools (Outils)** : Fonctions exécutables exposées avec un nom, une description et un schéma de paramètres JSON Schema (ex: `read_file`, `run_tests`).
* **Resources (Ressources)** : Données textuelles ou binaires en lecture seule (fichiers, logs, états).
* **Prompts** : Modèles de prompts réutilisables fournis par le serveur.

### Transports MCP
* **`stdio` (Standard Input/Output)** : Le client lance le serveur comme un sous-processus et communique via ses flux d'entrée/sortie standard. Idéal pour les outils locaux rapides.
* **`streamable HTTP` / SSE** : Communication réseau via requêtes HTTP avec streaming Server-Sent Events, permettant de connecter des serveurs distants ou hébergés dans des conteneurs.

### Dynamic Tool Introspection & Manual
Dans Agent Smith, l'agent ne connaît pas ses outils en dur dans le code du prompt. L'orchestrateur interroge dynamiquement le serveur MCP connecté (`list_tools`), extrait les signatures et descriptions, et construit automatiquement le "manuel de la sandbox" injecté dans le prompt système du LLM.

---

## 4. Sécurité, Sandboxing & Systèmes

### Qu'est-ce qu'une Sandbox (Bac à sable) ?
Un environnement d'exécution isolé imposant des barrières strictes pour empêcher du code non fiable d'endommager la machine hôte, de voler des données sensibles ou d'accaparer les ressources du système.

### Vecteurs d'Attaque & Escalade de Privilèges
Manières dont du code Python arbitraire généré par un LLM peut tenter d'échapper au contrôle :
* Importer des modules systèmes (`os`, `sys`, `subprocess`, `socket`).
* Utiliser la métaprogrammation Python pour remonter les hiérarchies de classes :
  `().__class__.__base__.__subclasses__()` pour retrouver un module non importé.
* Récupérer des références via `globals()`, `__builtins__`, ou `inspect`.
* Lancer des boucles infinies consommant 100% du CPU ou allouant toute la mémoire vive (Denial of Service - DoS).

### Techniques de Sécurisation (Standard Library uniquement)
Le sujet interdit formellement `RestrictedPython`. Les mécanismes doivent s'appuyer sur la bibliothèque standard :
1. **Analyse Statique par AST (Abstract Syntax Tree)** :
   * Parser le code généré via le module `ast` avant toute exécution (`ast.parse`).
   * Vérifier chaque nœud : rejeter formellement tout nœud `ast.Import` ou `ast.ImportFrom` ciblant des modules hors whitelist.
   * Interdire l'accès aux attributs privés ou dunders sensibles (`__subclasses__`, `__code__`, `__globals__`).
2. **Whitelisting des Builtins** :
   * Créer un dictionnaire de builtins minimaliste : conserver `len`, `range`, `print`, `int`, etc.
   * Supprimer ou neutraliser `eval`, `exec`, `compile`, `breakpoint`, `input`.
   * Remplacer `__import__` par un importeur filtré qui ne charge que les modules autorisés dans `SandboxConfig.authorized_imports`.
3. **Contrôle d'accès au système de fichiers (Filesystem Whitelisting)** :
   * Remplacer la fonction `open()` native par une version contrôlée vérifiant que le chemin résolu (`os.path.realpath`) est strictement inclus dans l'un des répertoires de `SandboxConfig.allowed_directories`.
4. **Plafonnement des Ressources (Resource Limiting)** :
   * Utilisation du module standard `resource` sous Linux :
     `resource.setrlimit(resource.RLIMIT_AS, (max_bytes, max_bytes))` pour borner la mémoire virtuelle.
5. **Isolation de Processus & Timeouts** :
   * Pourquoi un thread ne suffit pas : En Python, le GIL (Global Interpreter Lock) et l'absence d'interruption asynchrone sûre rendent impossible l'arrêt forcé d'un thread bloqué dans du calcul C ou une boucle infinie.
   * Exécution dans un **processus séparé** (`multiprocessing` ou `subprocess`) : permet d'appliquer un signal `SIGALRM` ou de tuer instantanément le processus récalcitrant avec `SIGKILL` sans affecter l'orchestrateur.

### Propagation des Exceptions
Les signaux de contrôle de flux Python (`KeyboardInterrupt` quand l'utilisateur fait Ctrl+C, ou `SystemExit`) ne doivent **jamais** être capturés silencieusement par un `except Exception:` générique. Ils doivent remonter pour permettre l'arrêt propre du programme.

---

## 5. Benchmarks & Évaluation de Code

### MBPP (Mostly Basic Python Problems)
* Benchmark universitaire contenant environ un millier d'énoncés de programmation élémentaire (manipulation de listes, chaînes, dictionnaires, algorithmes classiques).
* Chaque tâche fournit :
  * Une consigne textuelle (`task_definition`).
  * Une signature de fonction attendue (`function_definition`).
  * Une liste d'assertions de tests (`test_list`, ex: `assert remove_Occ("hello", "l") == "heo"`).

### SWE-bench & SWE-bench Verified
* Le standard de référence mondial pour évaluer les capacités de génie logiciel des IA.
* Constitué de véritables *Issues* GitHub résolues sur des dépôts open source majeurs (SymPy, Astropy, Django, Flask, scikit-learn...).
* **SWE-bench Verified** est un sous-ensemble filtré manuellement pour garantir que les tests et les consignes sont fiables et sans ambiguïté.
* L'agent doit produire un **patch git unifié** qui fait passer les tests unitaires du bug sans casser les tests existants.

### Unified Git Diff
* Format standardisé de comparaison de code généré par git.
* Commande imposée par le sujet : `git -c core.fileMode=false diff`.
* L'option `-c core.fileMode=false` ignore les modifications de droits d'accès aux fichiers (chmod) pour ne capturer que les modifications textuelles réelles.

### Métriques d'Analyse Agentique
* **Exploration Efficiency** : Numéro de l'itération à laquelle l'agent lit ou modifie pour la première fois le fichier qui finira dans le patch final. Un agent performant cible le bon module en 1 ou 2 étapes.
* **Partial Progress** : Numéro de l'itération où le nombre de tests en échec commence à diminuer par rapport à la baseline.
* **Submission Discipline** : Nombre d'itérations consommées inutilement entre le moment où les tests passent tous au vert et l'appel effectif à `final_answer`. L'idéal est 0 (soumission immédiate dès validation).

---

## 6. Gestion des API LLM, Quotas & Résilience

### Rate Limiting & Erreur HTTP 429
* **Rate Limiting** : Mécanisme mis en place par les hébergeurs d'API pour restreindre le nombre d'appels autorisés par utilisateur dans un intervalle de temps donné.
* **HTTP 429 (Too Many Requests)** : Code d'état renvoyé lorsque le quota de requêtes par minute (RPM) ou de tokens par minute (TPM) est atteint.

### Multi-Token Management & Rotation
* Nécessité dictée par le sujet : l'agent doit tourner sur des tiers gratuits sans bloquer l'évaluation.
* **Token Pool** : Stockage de plusieurs clés d'API valides pour un même fournisseur (ex: 3 clés OpenRouter différentes).
* **Stratégie de Rotation** :
  * *Round-Robin* : Alterner à chaque requête.
  * *On-Error Rotation* : Utiliser la clé courante, et basculer instantanément sur la suivante en cas d'erreur 429 avec mise en pause temporaire (*cooldown*) de la clé épuisée.

### Fallback Provider
Capacité de basculer vers un fournisseur de secours (ex: passer de Groq à OpenRouter ou Google AI Studio) si le premier est totalement indisponible (erreur serveur 500, panne d'infrastructure).

### Temps Wall-Clock vs CPU Time
* **Wall-Clock Time** : Durée réelle écoulée sur la montre entre le début et la fin d'une action (inclut les temps d'attente réseau des API et des I/O). C'est cette valeur qui est mesurée pour les timeouts stricts (120s pour MBPP, 900s pour SWE-bench).
* **CPU Time** : Temps durant lequel le processeur a effectivement exécuté du calcul.

---

## 7. Écosystème & Outillage Python Moderne

### `uv`
* Gestionnaire de paquets et d'environnements virtuels Python ultra-rapide écrit en Rust (conçu par Astral, les créateurs de Ruff).
* Remplace à lui seul `pip`, `virtualenv`, `pip-tools` et `poetry`.
* Commande d'exécution isolée : `uv run <commande>` (exécute un script ou un module dans l'environnement virtuel du projet sans devoir faire un `source venv/bin/activate` manuel).

### Pydantic v2
* Bibliothèque Python de validation de données et de sérialisation basée sur les annotations de types standard.
* Fournit des classes `BaseModel` qui garantissent que les données entrantes et sortantes respectent rigoureusement les types attendus, tout en générant des schémas JSON conformes.

### Signaux POSIX (`SIGTERM`, `SIGKILL`, `SIGALRM`)
* **`SIGALRM`** : Signal généré par le système d'exploitation après expiration d'un compte à rebours (`signal.alarm(seconds)`), utilisé pour interrompre un calcul trop long.
* **`SIGTERM` (Signal 15)** : Demande d'arrêt propre envoyée à un processus, lui laissant l'opportunité de fermer ses fichiers et nettoyer ses conteneurs Docker.
* **`SIGKILL` (Signal 9)** : Arrêt forcé et immédiat appliqué par le noyau Linux, impossible à intercepter ou ignorer.
