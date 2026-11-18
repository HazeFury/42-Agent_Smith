# Classement des Combinaisons Provider / Modèle pour Agent Smith

> **Contexte du projet :** Ce document évalue les meilleures combinaisons de fournisseurs d'API et de modèles d'IA pour le projet **Agent Smith** (cursus 42).  
> **Contrainte critique :** La solution doit reposer exclusivement sur les **quotas et tiers gratuits** (*free tiers*), sans carte bancaire, cartes de crédit prépayées ni forfaits payants, tout en restant capable de résoudre des tâches complexes du benchmark **SWE-bench** (limites : 300 000 tokens d'entrée, 10 000 tokens de sortie, 30 itérations max par tâche).

---

## 1. Méthodologie et Critères d'Évaluation

Le classement pondère à parts égales (50% / 50%) les deux critères suivants :

1. **Volume & Générosité du Tier Gratuit (G)** :
   - Requêtes journalières autorisées (RPD / *Requests Per Day*)
   - Débit minute (RPM / TPM : *Tokens Per Minute*)
   - Capacité de la fenêtre de contexte
   - Tolérance face aux sessions SWE-bench consommant jusqu'à 300 000 tokens d'entrée cumulés
2. **Efficacité sur le Benchmark SWE / Tâches de Code Réelles (S)** :
   - Capacité d'analyse et de localisation de bogues dans de gros dépôts (SymPy, Xarray, etc.)
   - Précision du *tool-calling* / génération de code exécutable
   - Formatage de patchs `git diff` conformes sans hallucinations

---

## 2. Tableau Récapitulatif : Top 10

| Rang | Fournisseur | Modèle | Note Quota (G /10) | Note SWE (S /10) | Note Moyenne (/10) | Statut Recommandé |
| :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **1** | **Google AI Studio** | `gemini-2.0-flash` / `gemini-1.5-pro` | 9.5 | 9.0 | **9.25** | **Pilier principal** |
| **2** | **Google AI Studio** | `gemini-1.5-flash` | 9.5 | 7.5 | **8.50** | **Prototypage / MBPP / Secours** |
| **3** | **NVIDIA (NIM)** | `meta/llama-3.3-70b-instruct` / `qwen2.5-coder-32b` | 8.0 | 8.5 | **8.25** | **Meilleur runner Llama/Qwen (H100)** |
| **4** | **OpenRouter** | `qwen/qwen-2.5-coder-32b-instruct:free` | 7.5 | 8.5 | **8.00** | **Meilleur modèle code open-source** |
| **5** | **Groq** | `llama-3.3-70b-versatile` | 7.5 | 8.0 | **7.75** | **Vitesse d'exécution maximale** |
| **6** | **NVIDIA (NIM)** | `deepseek-ai/deepseek-r1` | 7.5 | 9.0 | **8.25** | **Raisonnement profond sur infra dédiée** |
| **7** | **OpenRouter** | `meta-llama/llama-3.3-70b-instruct:free` | 7.5 | 8.0 | **7.75** | **Excellente alternative / Fallback** |
| **8** | **OpenRouter** | `deepseek/deepseek-r1:free` *(ou R1-distill)* | 6.5 | 9.0 | **7.75** | **Raisonnement (souvent en file d'attente)** |
| **9** | **Cloudflare Workers AI** | `@cf/qwen/qwen2.5-coder-32b-instruct` | 6.5 | 8.0 | **7.25** | **Spécialisé code & multi-token** |
| **10** | **Cohere** | `command-r-plus` / `command-r-08-2024` | 6.0 | 7.5 | **6.75** | **Tool use natif (quota mensuel restreint)** |

---

## 3. Analyse Détaillée par Fournisseur

### 3.1. Google AI Studio
- **Avantages majeurs :**
  - Quotas journaliers très élevés (ex. 1 500 RPD, 15 RPM et jusqu'à 1 million de TPM selon le modèle).
  - Fenêtre de contexte immense (1M à 2M tokens) éliminant tout risque d'oubli de contexte au cours des 30 itérations de SWE-bench.
  - Comportement d'agent et de diagnostic de bug éprouvé.
- **Points de vigilance :**
  - Nécessite de respecter le format de prompt pour éviter les réponses verbeuses hors code.

### 3.2. Groq
- **Avantages majeurs :**
  - Temps de réponse record (~250-300 tokens/sec), réduisant fortement le temps d'exécution global face au timeout de 900 secondes de SWE-bench.
  - Support de `llama-3.3-70b-versatile`, particulièrement doué en synthèse et structuration de code.
- **Points de vigilance :**
  - Les limites TPM (tokens par minute) peuvent être atteintes rapidement sur un gros repo : **rotation de tokens obligatoire**.

### 3.3. OpenRouter
- **Avantages majeurs :**
  - Accès aux modèles libres via le namespace `:free` (`qwen/qwen-2.5-coder-32b-instruct:free`, `llama-3.3-70b-instruct:free`, etc.).
  - Interface API compatible standard OpenAI (`/v1/chat/completions`), simplifiant l'architecture client.
- **Points de vigilance :**
  - Disponibilité variable en heure de pointe (temps d'attente ou rate-limits 429 périodiques nécessitant des retries exponentiels).

### 3.4. Cloudflare Workers AI
- **Avantages majeurs :**
  - Infrastructure stable, compatible OpenAI, catalogue incluant la famille Qwen 2.5 Coder et Llama 3.3.
- **Points de vigilance :**
  - Le palier gratuit alloue 10 000 *neurons* par jour, ce qui peut saturer après quelques tâches SWE-bench de 30 itérations. La rotation de plusieurs comptes / clés d'API est indispensable.

### 3.5. Cohere
- **Avantages majeurs :**
  - Modèle `command-r-plus` conçu spécifiquement pour le *Retrieval-Augmented Generation* (RAG) et les chaînes d'appels d'outils complexes.
- **Points de vigilance :**
  - Le tier gratuit d'essai (*Trial API key*) est limité à environ 1 000 requêtes par mois (et 20 RPM), ce qui en fait un fournisseur d'appoint plutôt qu'un moteur principal.

### 3.6. NVIDIA (NIM / API Catalog - build.nvidia.com)
- **Base URL :** `https://integrate.api.nvidia.com/v1` (100% compatible OpenAI `/chat/completions`).
- **Modèles recommandés :** `meta/llama-3.3-70b-instruct`, `qwen/qwen2.5-coder-32b-instruct`, `deepseek-ai/deepseek-r1`.
- **Avantages majeurs :**
  - Inférence hébergée directement sur infrastructure GPU NVIDIA H100/A100 avec optimisation TensorRT-LLM : latence ultra-faible et débit très élevé.
  - Zéro file d'attente publique (contrairement au free tier d'OpenRouter souvent saturé aux heures de pointe).
  - Dotation initiale de 1 000 crédits gratuits par compte sans carte bancaire requise. Avec le pool de 2 clés configuré dans `.env` (`NVIDIA_API_KEYS`), l'agent dispose d'une réserve de 2 000 requêtes haut de gamme.
  - Fenêtre de contexte jusqu'à 128k tokens, idéale pour absorber de gros contextes de code SWE-bench.
- **Points de vigilance :**
  - Il s'agit d'un pool de crédits d'évaluation : la rotation multi-clés (`NVIDIA_API_KEYS`) est indispensable pour pérenniser l'usage lors des longues campagnes de tests.

---

## 4. Recommandations Pratiques pour le Projet

1. **Architecture Multi-Provider recommandée :**
   - **Moteur Principal :** Google AI Studio (`gemini-2.0-flash` ou `gemini-1.5-pro`) pour ses quotas journaliers massifs (1 500 RPD) et sa fenêtre géante (1M tokens).
   - **Moteur Haute Performance (SWE-bench & Code) :** **NVIDIA NIM** (`meta/llama-3.3-70b-instruct` et `qwen/qwen2.5-coder-32b-instruct`) pour sa vitesse d'exécution sur H100 et sa précision sur le code.
   - **Moteur de Secours / Vitesse :** Groq (`llama-3.3-70b-versatile`) pour la rapidité instantanée et OpenRouter (`qwen/qwen-2.5-coder-32b-instruct:free`) en fallback.
2. **Stop Sequences indispensables :**
   - Spécifier systématiquement des séquences d'arrêt (ex: `<end_code>`, `\n```\n`, `</tool_call>`) pour couper la génération dès que le modèle émet un appel d'outil ou un bloc de code, évitant ainsi qu'il n'invente des observations fictives.
3. **Gestion des Tokens de Raisonnement :**
   - Pour les modèles de raisonnement comme `deepseek-r1`, surveiller attentivement le cumul des tokens d'output (limite stricte de 10 000 tokens imposée par le sujet).
