# Classement des Combinaisons Provider / Modèle pour Agent Smith

> **Contexte :** projet **Agent Smith** (cursus 42), benchmarks MBPP et SWE-bench.
> **Contrainte critique :** uniquement des **tiers gratuits**, sans carte bancaire. Limites du sujet : 300 000 tokens d'entrée, 10 000 tokens de sortie, 30 itérations max par tâche.
> **Date des mesures :** 2026-11-18. Les catalogues évoluent vite (les `gemini-2.5-*` et `gemini-1.5/2.0` cités dans l'ancienne version de ce document ne sont plus servis) : refaire le ping avant chaque campagne.

---

## 1. Méthodologie

### 1.1. Sélection
1. **Inventaire** : liste réelle des modèles exposés par chaque provider (`GET /models`, ou `/ai/models/search` pour Cloudflare) avec les clés du projet. Les modèles non-chat (embeddings, audio, image, modération, rerank) sont écartés.
2. **Ping** : un même prompt de code est envoyé à chaque candidat via `/chat/completions` (1ʳᵉ clé du pool, `max_tokens=3000`) :
   > *« Écris une fonction Python `merge_intervals(intervals)` qui fusionne les intervalles qui se chevauchent […]. Réponds uniquement avec un bloc ```python. »*
3. **Vérification** : le bloc de code renvoyé est exécuté sur 2 cas de test (`[[8,10],[1,3],[2,6],[15,18],[17,20]]` → `[[1,6],[8,10],[15,20]]`, et `[]` → `[]`).
4. Les échecs transitoires (503, 429, timeout) ont été relancés une fois avec un timeout de 150 s.

### 1.2. Note finale (moyenne de 3 critères, /10)
| Critère | Définition |
| :--- | :--- |
| **A — Accès** | Le modèle répond-il de façon fiable au ping ? Latence, absence de 429/503, disponibilité en tier gratuit, générosité du quota. |
| **S — Efficacité code** | Résultat du test (code exécutable et correct) + taille / réputation du modèle pour SWE-bench. |
| **T — Sobriété en tokens** | Tokens de sortie pour la même tâche (le sujet plafonne la sortie à 10 000 tokens et les modèles « raisonneurs » bavards épuisent le quota). |

> **Limites honnêtes de ce classement :** le test est une **tâche unique et courte**. A et T sont mesurés ; S combine ce test et la taille/réputation du modèle, il n'a **pas** été mesuré sur SWE-bench. Les quotas détaillés (RPD/TPM) n'ont pas été re-vérifiés pour cette version : seuls les 429/503 réellement observés sont rapportés.

---

## 2. Résultats bruts du ping

Légende : ✅ code correct au test · ❌ code incorrect · ⛔ erreur.

### Groq (`https://api.groq.com/openai/v1`)
| Modèle | Latence | In / Out | Résultat |
| :--- | ---: | :---: | :---: |
| `qwen/qwen3.8-27b` | 1.2 s | 62 / 118 | ✅ |
| `openai/gpt-oss-120b` | 1.0 s | 121 / 282 | ✅ |
| `openai/gpt-oss-20b` | 0.9 s | 121 / 454 | ✅ |

### NVIDIA NIM (`https://integrate.api.nvidia.com/v1`)
| Modèle | Latence | In / Out | Résultat |
| :--- | ---: | :---: | :---: |
| `nvidia/nemotron-3-ultra-550b-a55b` | 3.0 s | 68 / 225 | ✅ |
| `poolside/laguna-xs-2.1` | 2.9 s | 96 / 165 | ✅ |
| `nvidia/nemotron-3.5-bolt-e4b` | 2.9 s | 57 / 202 | ✅ |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | 5.8 s | 68 / 296 | ✅ |
| `nvidia/nemotron-3.5-lightning-30b-a3b` | 3.7 s | 68 / 639 | ✅ (gourmand) |
| `google/gemma-4-31b-it` | 10.0 s | 61 / 177 | ✅ (lent) |
| `meta/muse-glimmer-30b` | 56.2 s | 108 / 501 | ✅ (très lent) |
| `moonshotai/kimi-k3.1-pro` | 100 s | 139 / 399 | ✅ (inutilisable en latence) |
| `mistralai/mistral-large-4-1t-a52b`, `minimaxai/minimax-m3.1-flash`, `z-ai/glm-5.3-flash`, `stepfun-ai/step-5-preview` | — | — | ⛔ timeout > 150 s |

### Google AI Studio (`https://generativelanguage.googleapis.com/v1beta/openai`)
| Modèle | Latence | In / Out | Résultat |
| :--- | ---: | :---: | :---: |
| `gemini-3.5-flash-lite` | 1.6 s | 49 / 114 | ✅ |
| `gemini-3.1-flash-lite` | 2.2 s | 49 / 134 | ✅ |
| `gemini-3-flash-preview` | 3.7 s | 49 / 157 | ✅ |
| `gemma-4-26b-a4b-it` | 12.2 s | 49 / 155 | ❌ |
| `gemma-4-31b-it` | 42.1 s | 49 / 175 | ❌ |
| `gemini-3.5-flash`, `3.6-flash`, `3.7-flash` | — | — | ⛔ 503 (surcharge) |
| `gemini-3.8-flash` | — | — | ⛔ timeout |
| `gemini-3.1-pro-preview` | — | — | ⛔ 429 (pas de quota gratuit) |
| `gemini-2.5-flash`, `2.5-flash-lite`, `2.5-pro` | — | — | ⛔ 404 (retirés) |

### OpenRouter (modèles `:free`, `https://openrouter.ai/api/v1`)
| Modèle | Latence | In / Out | Résultat |
| :--- | ---: | :---: | :---: |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | 5.4 s | 68 / 225 | ✅ (un 503 au 1ᵉʳ essai) |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | 5.2 s | 68 / 303 | ✅ |
| `cohere/north-mini-code:free` | 4.4 s | 52 / 414 | ✅ |
| `nvidia/nemotron-3.5-lightning:free` | 5.0 s | 68 / 652 | ✅ (gourmand) |
| `recursive/flint-v1.0:free` | 4.0 s | 51 / 498 | ✅ |
| `inclusionai/ling-3.2-flash:free` | 17.0 s | 78 / 636 | ✅ (lent) |
| `baidu/ernie-5.5-flash-preview:free` | 4.2 s | 77 / 406 | ❌ |
| `google/gemma-4-31b-it:free`, `gemma-4-26b-a4b-it:free` | — | — | ⛔ 429 (2 essais) |
| `thinkingmachines/inkling-2-small:free` | — | — | ⛔ 403 (région) |

### Cloudflare Workers AI
| Modèle | Latence | In / Out | Résultat |
| :--- | ---: | :---: | :---: |
| `@cf/qwen/qwen2.5-coder-32b-instruct` | 3.3 s | 81 / 100 | ✅ |
| `@cf/nvidia/nemotron-3-120b-a12b` | 2.6 s | 68 / 268 | ✅ |
| `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | 5.2 s | 88 / 216 | ✅ |
| `@cf/qwen/qwen3.8-27b` | 9.0 s | 102 / 390 | ✅ |
| `@cf/openai/gpt-oss-20b` | 11.1 s | 119 / 574 | ✅ |
| `@cf/openai/gpt-oss-120b` | 14.1 s | 117 / 230 | ✅ (lent) |
| `@cf/google/gemma-4-26b-a4b-it` | 17.3 s | 64 / 1194 | ✅ (gourmand) |
| `@cf/moonshotai/kimi-k2.7-code`, `@cf/zai-org/glm-5.3-flash`, `@cf/deepseek-ai/deepseek-v4-flash-0731` | — | — | ⛔ 403 (hors plan Free) |

### Cohere (`https://api.cohere.ai/compatibility/v1`)
| Modèle | Latence | In / Out | Résultat |
| :--- | ---: | :---: | :---: |
| `command-a-03-2025` | 2.3 s | 48 / 166 | ✅ |
| `north-mini-code-1.0` | 2.4 s | 52 / 511 | ✅ |
| `command-a-plus-05-2026` | 2.6 s | 52 / 401 | ✅ |
| `command-r7b-12-2024` | 3.3 s | 48 / 211 | ✅ |
| `command-a-reasoning-08-2025` | 9.4 s | 48 / 1288 | ✅ (trop gourmand) |
| `command-r-08-2024`, `command-r-plus-08-2024` | ~3 s | 48 / ~160 | ❌ |

---

## 3. Classement final

| Rang | Provider | Modèle | A | S | T | **Note** | Rôle recommandé |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **1** | NVIDIA NIM | `nvidia/nemotron-3-ultra-550b-a55b` | 8 | 9 | 9 | **8.67** | **Principal SWE-bench** |
| **2** | Groq | `qwen/qwen3.8-27b` | 8 | 8 | 10 | **8.67** | **Principal MBPP / challenger SWE-bench** |
| **3** | Groq | `openai/gpt-oss-120b` | 8 | 9 | 8 | **8.33** | **Raisonnement / SWE-bench** |
| **4** | Google AI Studio | `gemini-3.1-flash-lite` | 8 | 7.5 | 9.5 | **8.33** | **Pilier stable Gemini** |
| **5** | NVIDIA NIM | `poolside/laguna-xs-2.1` | 8 | 7.5 | 9 | **8.17** | Code, bon rapport qualité/tokens |
| **6** | Google AI Studio | `gemini-3.5-flash-lite` | 7 | 7.5 | 10 | **8.17** | MBPP / itérations rapides |
| **7** | Google AI Studio | `gemini-3-flash-preview` | 7 | 8.5 | 9 | **8.17** | Raisonnement Gemini |
| **8** | Cloudflare | `@cf/qwen/qwen2.5-coder-32b-instruct` | 6 | 8 | 10 | **8.00** | Spécialiste code, le plus sobre |
| **9** | NVIDIA NIM | `nvidia/nemotron-3.5-bolt-e4b` | 8 | 6.5 | 9 | **7.83** | Ultra-léger MBPP / tests |
| **10** | OpenRouter | `nvidia/nemotron-3-ultra-550b-a55b:free` | 5 | 9 | 9 | **7.67** | Fallback du n°1 (file d'attente) |
| **11** | Cloudflare | `@cf/nvidia/nemotron-3-120b-a12b` | 6 | 8.5 | 8 | **7.50** | Secours puissant |
| **12** | Cohere | `command-a-03-2025` | 5 | 8 | 9 | **7.33** | Appoint (quota mensuel restreint) |
| **13** | Groq | `openai/gpt-oss-20b` | 8 | 7 | 7 | **7.33** | Tests rapides dans `main.py` |
| **14** | Cohere | `command-a-plus-05-2026` | 5 | 8.5 | 7.5 | **7.00** | Appoint, plus puissant |
| **15** | OpenRouter | `cohere/north-mini-code:free` | 5 | 8 | 7.5 | **6.83** | Fallback code |

### Meilleurs modèles par provider (liste reportée dans les commentaires de `.env`)
| Provider | 1er choix | 2ᵉ choix | 3ᵉ choix |
| :--- | :--- | :--- | :--- |
| **NVIDIA NIM** | `nvidia/nemotron-3-ultra-550b-a55b` | `poolside/laguna-xs-2.1` | `nvidia/nemotron-3.5-bolt-e4b` |
| **Groq** | `qwen/qwen3.8-27b` | `openai/gpt-oss-120b` | `openai/gpt-oss-20b` |
| **Google AI Studio** | `gemini-3.1-flash-lite` | `gemini-3.5-flash-lite` | `gemini-3-flash-preview` |
| **Cloudflare** | `@cf/qwen/qwen2.5-coder-32b-instruct` | `@cf/nvidia/nemotron-3-120b-a12b` | `@cf/meta/llama-3.3-70b-instruct-fp8-fast` |
| **OpenRouter** | `nvidia/nemotron-3-ultra-550b-a55b:free` | `cohere/north-mini-code:free` | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` |
| **Cohere** | `command-a-03-2025` | `command-a-plus-05-2026` | `north-mini-code-1.0` |

---

## 4. Analyse par fournisseur

### 4.1. NVIDIA NIM (build.nvidia.com)
- **Points forts :** 100 % compatible OpenAI ; latence stable ~3 s sur les modèles Nemotron/Laguna ; Nemotron-3-Ultra (550B) est à la fois sobre (225 tokens) et correct. Pool de 2 clés dans `NVIDIA_API_KEYS`.
- **Vigilance :** crédits d'évaluation (pool limité, rotation de clés indispensable). Plusieurs gros modèles du catalogue sont **inutilisables** : timeouts > 150 s (Mistral Large 4, MiniMax, GLM, Step) ou 100 s (Kimi K3.1). Ne pas les inclure dans la chaîne de repli.
- `nemotron-3.5-lightning-30b-a3b` : raisonnement natif, mais 639 tokens pour une tâche triviale → à réserver à la planification.

### 4.2. Groq
- **Points forts :** latence ~1 s, ce qui laisse une large marge face au timeout de 900 s de SWE-bench. `qwen/qwen3.8-27b` est le plus sobre du lot (118 tokens). `gpt-oss-120b` : contexte 131k.
- **Vigilance :** les limites TPM se saturent vite sur de gros dépôts : **rotation des 2 clés obligatoire** (`GROCK_API_KEYS`, nom de variable à conserver tel quel côté code). Catalogue réduit (3 modèles de chat).

### 4.3. Google AI Studio (Gemini)
- **Points forts :** fenêtre de contexte très grande ; les modèles `flash-lite` sont rapides (1.6-2.2 s) et sobres.
- **Vigilance :** catalogue instable. Les `gemini-3.5/3.6/3.7/3.8-flash` renvoient des 503 (« high demand ») et `gemini-3.1-pro-preview` un 429 : **pas de gros modèle fiable en gratuit aujourd'hui**. Les `gemma-4-*` sont lents et ont échoué au test. Les `gemini-2.5-*` sont retirés (404).
- Clé au format `AQ.…` acceptée par l'endpoint OpenAI-compatible.

### 4.4. Cloudflare Workers AI
- **Points forts :** `qwen2.5-coder-32b` est le plus sobre de tous les modèles testés (100 tokens), 3.3 s. Compatible OpenAI via `/accounts/<id>/ai/v1`.
- **Vigilance :** les gros modèles récents (Kimi K2.7, GLM 5.3 Flash, DeepSeek V4) sont **refusés en plan Free (403)**. Quota gratuit de 10 000 *neurons*/jour (valeur de l'ancienne version, non re-vérifiée) : à surveiller. Pas d'endpoint `/models` : utiliser `/ai/models/search`. La variable d'environnement s'appelle `CLOUDFLARE_COUNT_ID` (sic, pour *account id*).

### 4.5. OpenRouter (`:free`)
- **Points forts :** donne accès à Nemotron-3-Ultra et `north-mini-code` en doublon des autres providers, donc un fallback de plus.
- **Vigilance :** disponibilité aléatoire (503 puis succès sur Nemotron-Ultra, 429 persistants sur les Gemma, 403 région sur Inkling). Le catalogue gratuit est réduit à 14 modèles.

### 4.6. Cohere
- **Points forts :** `command-a-03-2025` est correct et sobre (166 tokens, 2.3 s).
- **Vigilance :** `command-r-08-2024` et `command-r-plus-08-2024` ont échoué au test ; `command-a-reasoning` consomme 1288 tokens. Quota Trial restreint (~1 000 requêtes/mois d'après l'ancienne version) : fournisseur d'appoint uniquement.

---

## 5. Recommandations pratiques

1. **Chaîne de repli suggérée (SWE-bench) :**
   `NVIDIA nemotron-3-ultra-550b` → `Groq gpt-oss-120b` → `Groq qwen3.8-27b` → `Gemini 3.1-flash-lite` → `OpenRouter nemotron-3-ultra:free`.
2. **MBPP / tests rapides :** `Groq qwen3.8-27b` ou `gpt-oss-20b`, `Gemini 3.5-flash-lite`, `NVIDIA nemotron-3.5-bolt-e4b`.
3. **Providers d'appoint (quota faible ou instable) :** Cloudflare, Cohere, OpenRouter.
4. **Une seule classe client :** tous ces modèles sont servis par `OpenAICompatibleClient` ; seuls `base_url`, `api_key` et `model_name` changent.
5. **Stop sequences :** spécifier systématiquement des séquences d'arrêt (ex. `<end_code>`, `\n```\n`, `</tool_call>`) pour couper la génération dès qu'un appel d'outil ou un bloc de code est émis.
6. **Tokens de raisonnement :** certains modèles renvoient leur réponse dans `reasoning_content` plutôt que `content` (déjà géré dans `generate()`). Surveiller le cumul de tokens de sortie (limite stricte de 10 000).
7. **Résilience :** prévoir des retries avec backoff pour les 503/429 observés (Gemini, OpenRouter) et un timeout par requête (60 s actuellement dans `generate()` : insuffisant pour Kimi/Muse, volontairement exclus).
