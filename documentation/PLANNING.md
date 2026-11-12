# Planning & Répartition des Rôles — Agent Smith

Ce planning est spécialement dimensionné pour un travail en binôme entre **Marco** et **Steph**.
Il optimise le parallélisme en séparant clairement le volet **Système / Sécurité / Infrastructure** et le volet **IA / Orchestration / Prompts**, tout en prévoyant des points de synchronisation réguliers et une préparation conjointe à l'examen.

---

## 👥 Profils & Répartition des Responsabilités

| Domaine | Marco 🛠️ (Spécialiste Système & Sécurité) | Steph 🧠 (Spécialiste IA & Orchestration) |
| :--- | :--- | :--- |
| **Cœur de métier** | Sandbox, Sécurité AST/Builtins, Protocoles MCP, Docker & Gestion des processus Unix. | Moteur LLM, Gestion multi-tokens/quotas, Boucle ReAct, Prompts & Stratégie Benchmark. |
| **Modules assignés** | `src/sandbox/`, `src/mcp/`, `mcp_tools_*.py`, isolation Docker. | `src/llm/`, `src/agent/`, extracteur de code, prompts dynamiques. |
| **Responsabilité commune** | Contrats de données Pydantic, intégration de bout en bout, campagne de benchmark, entraînements au live-coding pour la soutenance. |

---

## 📅 Planning par Jalons (Roadmap sur 5 Semaines)

```
       MARCO (Système & Sécurité)                  STEPH (IA & Orchestration)
 ┌──────────────────────────────────────┐    ┌──────────────────────────────────────┐
 │ S1 : Sandbox Sécurisée + Mode REPL   │    │ S1 : Client LLM Multi-Token & Quotas │
 └──────────────────┬───────────────────┘    └──────────────────┬───────────────────┘
                    │                                           │
                    ▼                                           ▼
 ┌──────────────────────────────────────┐    ┌──────────────────────────────────────┐
 │ S2 : Serveur MCP MBPP + Stdio Bridge │    │ S2 : Boucle ReAct & Extraction Code  │
 └──────────────────┬───────────────────┘    └──────────────────┬───────────────────┘
                    │                                           │
                    └───────────────► JALON 1 ◄─────────────────┘
                               Premier run MBPP réussi
                                        │
                    ┌───────────────────┴───────────────────┐
                    ▼                                       ▼
 ┌──────────────────────────────────────┐    ┌──────────────────────────────────────┐
 │ S3 : Outils SWE-bench & Docker       │    │ S3 : Optimisation Tokens MBPP & Eval │
 └──────────────────┬───────────────────┘    └──────────────────┬───────────────────┘
                    │                                           │
                    └───────────────► JALON 2 ◄─────────────────┘
                           Validation exam_mbpp (4/5)
                          + exam_sandbox (100% réussi)
                                        │
                    ┌───────────────────┴───────────────────┐
                    ▼                                       ▼
 ┌──────────────────────────────────────┐    ┌──────────────────────────────────────┐
 │ S4 : Intégration Docker SWE-bench    │    │ S4 : Prompt SWE-bench & Résolution   │
 └──────────────────┬───────────────────┘    └──────────────────┬───────────────────┘
                    │                                           │
                    └───────────────► JALON 3 ◄─────────────────┘
                          Validation exam_swebench (2/3)
                                        │
                    ┌───────────────────┴───────────────────┐
                    ▼                                       ▼
 ┌──────────────────────────────────────┐    ┌──────────────────────────────────────┐
 │ S5 : README.md, Clean & Sécurité     │    │ S5 : Benchmark Report (5 modèles)    │
 └──────────────────┬───────────────────┘    └──────────────────┬───────────────────┘
                    │                                           │
                    └───────────────► JALON 4 ◄─────────────────┘
                             Simulation Soutenance 42
                         (Entraînement Live-Coding 2-5 min)
```

---

### Semaine 1 : Fondations & Découplage Initial

> **Objectif de la semaine** : Avoir les deux composants autonomes fonctionnels et testés unitairement sans dépendre l'un de l'autre.

* **Jour 1 (En commun)** :
  - Initialisation de l'environnement avec `uv` et Python 3.10.
  - Définition stricte des modèles Pydantic partagés (`src/models/`) : `SandboxConfig`, `StepMetrics`, `SolutionOutput`, `MBPPTaskInput`, `SWEBenchTaskInput`.
  - Configuration du linter/formateur (`ruff`), typing strict (`mypy`).

* **Marco (Track Sandbox & Sécurité)** :
  - Création du moteur d'exécution de code Python isolé dans un sous-processus (`multiprocessing` ou `subprocess`).
  - Analyse statique AST du code avant exécution pour bloquer les imports interdits et attributs dunder suspects.
  - Surcharge des builtins dangereux (`eval`, `exec`, `open` sauvage).
  - Implémentation du contrôle de chemin sur le système de fichiers (`allowed_directories`).
  - Limitation de la mémoire RAM (`resource.setrlimit`) et timeout strict.
  - CLI `uv run sandbox` avec mode REPL interactif.

* **Steph (Track LLM & Résilience)** :
  - Création de l'abstraction multi-fournisseurs (OpenRouter, Groq, Gemini/Google AI Studio, Together AI).
  - Implémentation du `KeyManager` : chargement des clés d'API depuis `.env` ou variables d'environnement.
  - Gestion automatique des rate-limits (HTTP 429) : bascule transparente de clé (Token Rotation) avec cooldown.
  - Calcul et journalisation précise des tokens consommés (`input_tokens`, `output_tokens`, `request_time_ms`, `retries`).
  - Injection des `stop_sequences` pour couper la génération dès que le modèle termine un bloc de code.

---

### Semaine 2 : Le Protocole MCP & Première Boucle Agent (MBPP)

> **Objectif de la semaine** : Connecter l'orchestrateur au bac à sable et réussir à faire résoudre un problème MBPP simple en autonomie.

* **Marco** :
  - Implémentation du protocole MCP (transports `stdio` et `streamable HTTP`).
  - Écriture du serveur MCP MBPP à la racine : `mcp_tools_mbpp.py`.
  - Implémentation de l'outil `run_tests(code, test_list)`.
  - Bridge MCP dans la sandbox : exposer dynamiquement les outils MCP connectés sous forme de fonctions Python appelables par l'agent.
  - Injection de la fonction native `final_answer(code)` dans la sandbox.

* **Steph** :
  - Conception de la boucle agent (orchestrateur `Thought → Code → Observation`).
  - Génération dynamique du manuel d'outils (Sandbox Manual) à partir des schémas JSON du serveur MCP connecté.
  - Couche d'extraction de code : extraction regex/parser des blocs de code Python et gestion des formats alternatifs (XML Anthropic, JSON Hermes).
  - Gestion du feedback d'erreur envoyé au LLM (code manquant, code malformé, timeout partiel).

* **Fin de Semaine 2 (En commun)** :
  - **Connexion Orchestrateur + Sandbox** : Exécution de bout en bout sur une tâche MBPP simple.
  - Validation de la génération du fichier de sortie `solution.json`.

---

### Semaine 3 : Durcissement MBPP & Préparation SWE-bench

> **Objectif de la semaine** : Valider définitivement la suite de tests de sécurité et garantir 4/5 réussites sur MBPP sous les plafonds stricts.

* **Marco** :
  - Passage au crible des tests de sécurité du sujet (`exam_sandbox.sh`) : s'assurer qu'aucune tentative de bypass ne passe.
  - Implémentation du serveur d'outils SWE-bench `mcp_tools_swebench.py` :
    - Fichiers : `read_file` (format `cat -n`), `edit_file`, `list_files`.
    - Code search : `search_code`, `search_function_or_class_definition_in_code`, `find_references`.
    - Exécution : `run_tests()`, `get_patch()`, `run_command()`.
    - Prise en compte impérative de la variable `TESTBED_PATH`.

* **Steph** :
  - Optimisation des prompts et de la gestion de contexte pour MBPP :
    - Respecter les limites dures : **Max 10 itérations**, **Max 6 000 tokens in**, **Max 1 500 tokens out**, **Timeout 120s**.
  - CLI `uv run python -m agent_mbpp`.
  - Exécution en boucle sur les tâches MBPP de la moulinette (`moulinette_eval dump/validate`).
  - Atteinte du seuil de réussite de **4/5**.

---

### Semaine 4 : Résolution de Bugs Réels (SWE-bench & Docker)

> **Objectif de la semaine** : Déployer l'agent face à de vrais dépôts conteneurisés et valider au moins 2 tâches sur 3.

* **Marco** :
  - Orchestration des conteneurs Docker pour SWE-bench (images `swebench/sweb.eval.x86_64...`).
  - Choix d'architecture : Host MCP bridge vers Docker (`docker exec`) ou déploiement de la sandbox dans le conteneur.
  - Gestion du cycle de vie des conteneurs : nettoyage automatique garanti, y compris sur réception de `SIGTERM`/`SIGKILL` (signal handlers).
  - Extraction fiable du patch unifié : `git -c core.fileMode=false diff`.

* **Steph** :
  - Spécialisation du prompt pour le diagnostic logiciel :
    - Méthodologie d'exploration : chercher le bug -> reproduire avec `run_tests` -> cibler avec `edit_file` -> vérifier -> appeler `final_answer(get_patch())`.
  - Tronquage intelligent des sorties de fichiers trop volumineux pour ne pas exploser le plafond de **300 000 tokens**.
  - CLI `uv run python -m agent_swebench`.

* **Fin de Semaine 4 (En commun)** :
  - Tests sur les instances recommandées : `sympy__sympy-14711`, `sympy__sympy-13480`, `pydata__xarray-4629`.
  - Validation du script d'évaluation officiel : `exam_swebench.sh` avec au moins **2/3 tâches réussies** dans la limite des 900s.

---

### Semaine 5 : Campagne de Benchmark, Documentation & Soutenance

> **Objectif de la semaine** : Produire tous les livrables obligatoires et être incollables pour la soutenance.

* **Steph** :
  - Pilotage de la campagne de benchmark pour `BENCHMARK_REPORT.md` :
    - 5 modèles différents (ex: Claude 3.5 Sonnet / Qwen 2.5 Coder / Llama 3.3 / DeepSeek / Gemini Flash).
    - Au moins 2 providers gratuits distincts.
    - Évaluation sur les 3 mêmes tâches SWE-bench.
  - Mesure des métriques intermédiaires (exploration efficiency, submission discipline) et étude d'ablation.
  - Rédaction des analyses et conclusions du rapport.

* **Marco** :
  - Rédaction du `README.md` en anglais avec l'en-tête officiel 42 requis.
  - Audit de sécurité pré-rendu : vérification stricte qu'aucune clé API ne traîne dans le git (`git log -S "sk-"`).
  - Vérification de l'absence de fichiers temporaires, conteneurs fantômes ou poids de modèles.

* **Ensemble (Préparation intensive à la soutenance)** :
  - **Drill "Live-Coding 2-5 minutes"** :
    - Marco donne un exercice à Steph (ex: "ajoute un flag `--verbose` à la sandbox" ou "modifie le format d'output de `read_file`").
    - Steph donne un exercice à Marco (ex: "change la stop sequence du provider Groq" ou "ajoute un nouveau builtin autorisé").
    - Répéter jusqu'à ce que les deux membres soient capables de modifier n'importe quelle partie du projet les yeux fermés.

---

## 📋 Matrice des Responsabilités (RACI)

* **R (Responsible)** : Fait le travail.
* **A (Accountable)** : Valide et garantit la conformité.
* **C (Consulted)** : Contribue ou conseille.
* **I (Informed)** : Tenu au courant de l'avancement.

| Tâche / Livrable | Marco | Steph | Validation / Livrable attendu |
| :--- | :---: | :---: | :--- |
| Modèles Pydantic communs | **R** | **R** | `src/models/*.py` complets et validés |
| Sandbox & Isolation AST/Builtins | **R/A** | **C** | `exam_sandbox.sh` 100% vert |
| Mode interactif `uv run sandbox` | **R** | **I** | REPL opérationnel |
| Client LLM, Quotas & Rotation 429 | **C** | **R/A** | Zéro crash sur rate-limits |
| Serveurs MCP & Outils de base | **R/A** | **C** | `mcp_tools_mbpp.py` & `swebench.py` |
| Boucle ReAct & Extraction de code | **C** | **R/A** | Extraction sans faille de code Python |
| Agent MBPP & Optimisation tokens | **C** | **R/A** | `exam_mbpp.sh` $\ge 4/5$ |
| Outils SWE-bench, Docker & Git Diff | **R/A** | **C** | Nettoyage conteneurs & diff valide |
| Agent SWE-bench & Stratégie Prompt | **C** | **R/A** | `exam_swebench.sh` $\ge 2/3$ |
| Rapport de Benchmark | **C** | **R/A** | `BENCHMARK_REPORT.md` (5 modèles) |
| README officiel 42 | **R/A** | **C** | `README.md` en anglais conforme |
| Maîtrise Live-Coding Soutenance | **R/A** | **R/A** | 100% de réussite sur modif 2-5 min |

---

## 💡 Règles d'or de collaboration pour réussir le projet à deux

1. **Aucun code "boîte noire"** : La règle d'évaluation 42 stipule que chaque membre peut être interrogé sur n'importe quel fichier. Marco doit comprendre le fonctionnement de l'orchestrateur et Steph doit comprendre la sécurité de la sandbox.
2. **Revue de code obligatoire (Pull Requests)** : Aucune branche n'est fusionnée sur `main` sans la validation de l'autre.
3. **Tester tôt avec la moulinette** : Ne jamais attendre la dernière semaine pour tester les scripts d'examen fournis (`exam_mbpp.sh`, `exam_swebench.sh`, `exam_sandbox.sh`).
4. **Attention aux quotas gratuits** : Créez dès le début vos comptes indépendants sur OpenRouter, Groq et Google AI Studio pour cumuler un pool de clés suffisant pour le benchmark final.
