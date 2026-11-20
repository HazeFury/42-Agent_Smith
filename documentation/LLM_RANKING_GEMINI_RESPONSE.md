# Classement des Combinaisons Provider / Modèle pour Agent Smith

> **Contexte du projet :** Ce document synthétise l'audit en direct et le classement des meilleures combinaisons de fournisseurs d'API et de modèles d'IA pour le projet **Agent Smith** (cursus 42).
> **Contrainte critique :** La solution repose exclusivement sur les **quotas et tiers gratuits** (*free tiers*), sans carte bancaire, tout en respectant les limites imposées par le sujet SWE-bench :
> - Cumul d'entrée maximal : **300 000 tokens**.
> - Cumul de sortie maximal : **10 000 tokens**.
> - Nombre maximal d'itérations : **30 itérations** par tâche.
> - Timeout global par instance : **900 secondes**.

---

## 1. Méthodologie et Critères d'Évaluation

Chaque modèle a été audité via des tests de connectivité en direct (*ping HTTP 200*), analyse de latence, économie de tokens et précision sur le code. La note finale est calculée sur deux axes majeurs :

1. **Volume & Générosité du Tier Gratuit (G /10)** :
   - Quota journalier (RPD) et débit minute (RPM / TPM).
   - Capacité de la fenêtre de contexte ($\ge 128\text{k}$ tokens).
   - Stabilité face aux erreurs 429 et disponibilité réelle sans file d'attente bloquante.
2. **Efficacité Code & Économie en Tokens (S /10)** :
   - Précision dans la localisation de bugs et respect de la syntaxe de patchs diff (SWE-bench).
   - Efficacité algorithmique sans verbiage superflu (MBPP).
   - Consommation raisonnable des 10 000 tokens d'output autorisés.

---

## 2. Tableau Récapitulatif : Classement Final

| Rang | Fournisseur | Modèle Cible (ID exact) | Statut Ping | Note Quota (G) | Note Code (S) | Note Globale (/10) | Rôle Recommandé |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **1** | **NVIDIA NIM** | `nvidia/nemotron-3-ultra-550b-a55b` | **200 OK** | 8.5 | 9.5 | **9.00** | **Pilier SWE-bench (Flagship 550B)** |
| **2** | **Groq** | `openai/gpt-oss-120b` | **200 OK** | 8.5 | 9.0 | **8.75** | **Vitesse extrême & SWE-bench (500 tps)** |
| **3** | **Cloudflare AI** | `@cf/qwen/qwen2.5-coder-32b-instruct` | **200 OK** | 8.0 | 9.0 | **8.50** | **Référence mondiale Code (Qwen 32B)** |
| **4** | **Google Gemini** | `gemini-3.5-flash-lite` | **200 OK** | 9.5 | 7.5 | **8.50** | **Contexte géant (1M) & Résilience** |
| **5** | **Groq** | `qwen/qwen3.8-27b` | **200 OK** | 8.0 | 8.5 | **8.25** | **Tool-calling & MBPP haute cadence** |
| **6** | **NVIDIA NIM** | `nvidia/nemotron-3.5-lightning-30b-a3b` | **200 OK** | 8.5 | 8.0 | **8.25** | **Raisonnement CoT & Stratégie pré-patch** |
| **7** | **OpenRouter** | `cohere/north-mini-code:free` | **200 OK** | 7.5 | 8.5 | **8.00** | **Expert code dédié 100% gratuit** |
| **8** | **Cohere** | `command-r-08-2024` | **200 OK** | 7.0 | 8.5 | **7.75** | **RAG / Tool use natif (128k context)** |
| **9** | **Groq** | `openai/gpt-oss-20b` | **200 OK** | 8.5 | 7.0 | **7.75** | **Ultra-rapide (1 000 tps) / Tests & MBPP** |
| **10** | **NVIDIA NIM** | `nvidia/nemotron-3.5-bolt-e4b` | **200 OK** | 8.5 | 6.5 | **7.50** | **Économie tokens maximale / Prototypage** |

---

## 3. Analyse Détaillée par Fournisseur

### 3.1. NVIDIA NIM (`https://integrate.api.nvidia.com/v1`)
- **Format API :** 100% compatible OpenAI (`/chat/completions`).
- **Modèles testés et validés :**
  - `nvidia/nemotron-3-ultra-550b-a55b` : Modèle géant de 550 milliards de paramètres hébergé sur clusters NVIDIA H100. Capacités de raisonnement et de génération de patchs équivalentes aux meilleurs modèles propriétaires.
  - `nvidia/nemotron-3.5-lightning-30b-a3b` : Modèle MoE 30B avec réflexion intégrée (`reasoning_content`), parfait pour la phase d'analyse avant modification de code.
  - `nvidia/nemotron-3.5-bolt-e4b` : Modèle 4B ultra-léger et économique pour les vérifications rapides.
- **Gestion des quotas :** Dotation gratuite de 1 000 crédits par compte, démultipliée par le pool de clés (`NVIDIA_API_KEYS`).

### 3.2. Groq Cloud (`https://api.groq.com/openai/v1`)
- **Format API :** 100% compatible OpenAI (`/chat/completions`).
- **Modèles testés et validés :**
  - `openai/gpt-oss-120b` : Flagship 120B tournant à ~500 tokens/sec. Idéal pour ne pas dépasser le timeout de 900s de SWE-bench.
  - `qwen/qwen3.8-27b` : Rigueur syntaxique exceptionnelle pour les structures de données et le formatage de code Python.
  - `openai/gpt-oss-20b` : Vitesse record (~1 000 tokens/sec). Idéal pour les exercices algorithmiques courts de MBPP.
- **Attention dépréciations :** `llama-3.1-8b-instant` et `llama-3.3-70b-versatile` ont été retirés du catalogue Groq.

### 3.3. Google Gemini (`https://generativelanguage.googleapis.com/v1beta/openai`)
- **Format API :** Point de terminaison officiel compatible OpenAI standard.
- **Modèles testés et validés :**
  - `gemini-3.5-flash-lite` & `gemini-flash-lite-latest` : Modèles très stables, latence basse, et bénéficiant d'une fenêtre de contexte de 1 000 000 tokens.
  - `gemini-3.8-flash` : Très puissant mais sujet à des saturations temporaires (HTTP 503) aux heures d'affluence.
- **Points forts :** Quotas journaliers parmi les plus massifs du marché en version gratuite, parfaits pour absorber les historiques de 30 tours de dialogue.
- **Attention dépréciations :** Les anciennes versions `gemini-1.5-flash` et `gemini-2.0-flash` renvoient une erreur 404.

### 3.4. Cloudflare Workers AI (`https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1`)
- **Format API :** 100% compatible OpenAI (`/chat/completions`).
- **Modèles testés et validés :**
  - `@cf/qwen/qwen2.5-coder-32b-instruct` : Le meilleur modèle open-weight mondial pour l'ingénierie logicielle (HumanEval > 85%).
  - `@cf/meta/llama-3.3-70b-instruct-fp8-fast` : Inférence accélérée FP8 sur infrastructure globale Cloudflare Edge.
- **Points forts :** Stabilité réseau et pas de files d'attente.

### 3.5. OpenRouter (`https://openrouter.ai/api/v1`)
- **Format API :** 100% compatible OpenAI (`/chat/completions`).
- **Modèles testés et validés (Namespace `:free`) :**
  - `cohere/north-mini-code:free` : Entraîné spécifiquement sur le code source Python, direct et concis.
  - `nvidia/nemotron-3-ultra-550b-a55b:free` : Accès gratuit au modèle 550B en secours de l'API NVIDIA directe.
  - `nvidia/nemotron-3.5-lightning:free` : Raisonnement CoT gratuit.
- **Points de vigilance :** Risque de limitation 429 lors des pics d'utilisation mondiaux.

### 3.6. Cohere (`https://api.cohere.com/v2/chat`)
- **Format API :** Format natif Cohere v2 (messages avec type texte).
- **Modèles testés et validés :**
  - `command-r7b-12-2024` : Modèle 7B économe avec 132k tokens de contexte.
  - `command-r-08-2024` : Modèle 128k optimisé pour les appels d'outils et le raisonnement structuré.
  - `command-a-03-2025` : Modèle flagship de dernière génération (contexte géant de 288k tokens).

---

## 4. Stratégie Opérationnelle pour Agent Smith

Pour maximiser les scores tout en garantissant zéro dépassement de quotas :

1. **Stratégie SWE-bench (Tâches complexes multi-fichiers) :**
   - **Moteur Principal :** `nvidia/nemotron-3-ultra-550b-a55b` (NVIDIA NIM) ou `openai/gpt-oss-120b` (Groq).
   - **Fallback immédiat sur 429 :** Rotation de clé dans `NVIDIA_API_KEYS`, puis bascule vers `@cf/qwen/qwen2.5-coder-32b-instruct` (Cloudflare).
2. **Stratégie MBPP (Fonctions Python simples & rapides) :**
   - **Moteur Principal :** `openai/gpt-oss-20b` (Groq) pour sa latence quasi instantanée (~1 000 tps).
   - **Alternative économique :** `gemini-3.5-flash-lite` ou `cohere/north-mini-code:free`.
3. **Économie de tokens (Règle des 10 000 tokens de sortie) :**
   - Utiliser des prompts concis interdisant les dissertations théoriques.
   - Poser systématiquement des séquences d'arrêt : `stop_sequences=["\n```\n", "<end_code>"]`.

GEMINI
 Base URL: https://generativelanguage.googleapis.com/v1beta/openai
 gemini-3.5-flash-lite — Recommandé (Rapide, stable, 1M tokens context)
 gemini-flash-lite-latest — Alias automatique vers la dernière version flash-lite
 gemini-3.8-flash — Modèle multimodal puissant (sujet à 503 en heure de pointe)
 (Note: gemini-1.5-flash et gemini-2.0-flash sont dépréciés/404)

GROCK
 Base URL: https://api.groq.com/openai/v1
 openai/gpt-oss-120b — Le Flagship (Le successeur pour SWE-bench)
 Taille : 120B | Vitesse : ~500 tps | Contexte : 131k tokens
 Forces : Raisonnement complexe et génération de code.

 qwen/qwen3.8-27b — L'expert en ingénierie logicielle
 Taille : 27B | Vitesse : ~450 tps | Contexte : 131k tokens
 Forces : Rigueur tool-calling et manipulation de structures.

 openai/gpt-oss-20b — La formule 1 pour les tests et MBPP
 Taille : 20B | Vitesse : ~1 000 tps | Contexte : 131k tokens
 Forces : Quasiment instantané, très économe en tokens/quotas.
 (Note: llama-3.1-8b et llama-3.3-70b sont dépréciés sur Groq)

NVIDIA
 Base URL: https://integrate.api.nvidia.com/v1
 nvidia/nemotron-3-ultra-550b-a55b — Candidat Flagship (SWE-bench)
 Taille : 550B | Infra : NVIDIA H100 | Contexte : 128k tokens
 Forces : Raisonnement lourd, patchs complexes et diagnostic de bugs.

 nvidia/nemotron-3.5-lightning-30b-a3b — Raisonnement & Planification
 Taille : 30B MoE | Chaîne de pensée native (reasoning_content).
 Forces : Établir la stratégie de résolution avant génération du patch.

 nvidia/nemotron-3.5-bolt-e4b — Ultra-rapide / MBPP & Tests
 Taille : 4B | Vitesse ultra-rapide, consommation minimale de quotas.

OPENROUTER
 Base URL: https://openrouter.ai/api/v1
 cohere/north-mini-code:free — Expert code gratuit
 Forces : Spécialisé code Python, temps de réponse rapide, 100% gratuit.

 nvidia/nemotron-3-ultra-550b-a55b:free — Modèle 550B gratuit
 Forces : Même modèle géant que NVIDIA NIM, disponible en fallback gratuit.

 nvidia/nemotron-3.5-lightning:free — Raisonnement gratuit
 Forces : Modèle de raisonnement avec chaîne de pensée sans consommer de crédits.

CLOUDFLARE
 Base URL: https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_COUNT_ID}/ai/v1
 @cf/qwen/qwen2.5-coder-32b-instruct — L'étalon open-source pour le code
 Forces : Précision syntaxique extrême, inférence Cloudflare Edge.

 @cf/meta/llama-3.3-70b-instruct-fp8-fast — Llama 3.3 70B accéléré
 Forces : Modèle 70B quantifié FP8 pour une exécution ultra-rapide.

COHERE_API_KEYS
 Endpoint API: https://api.cohere.com/v2/chat
 command-r7b-12-2024 — Modèle 7B ultra-rapide (132k context)
 Forces : Faible latence, économe en tokens, parfait pour les sous-tâches.

 command-r-08-2024 — Le standard Tool-Calling / RAG (128k context)
 Forces : Spécialisé dans les appels d'outils et le suivi strict d'instructions.

 command-a-03-2025 — Flagship Cohere nouvelle génération (288k context)
 Forces : Contexte étendu (288k tokens), raisonnement et synthèse.
