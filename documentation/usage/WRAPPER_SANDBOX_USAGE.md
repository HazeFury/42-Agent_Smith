# Fonctionnement des Wrappers d'Outils et de la Sandbox

Ce document explique le mécanisme d'interception et de circulation des appels d'outils entre le code généré par le LLM, la Sandbox sécurisée, le pont (*Bridge*), le Client MCP et le Serveur MCP.

---

## 1. Contexte & Problématique Architecturale

Dans le projet **Agent Smith**, notre agent est un **Code Agent** :
1. Le LLM résout des problèmes en écrivant directement du **vrai code Python** (et non des appels JSON natifs).
2. Ce code généré par l'IA est exécuté localement dans un **bac à sable sécurisé (Sandbox)** via `exec(code, sandbox_globals)`.
3. Pour des raisons strictes de sécurité, la Sandbox **interdit tout accès direct au système de fichiers, au réseau ou aux commandes système**.
4. Les outils réels (`read_file`, `edit_file`, `run_tests`, etc.) sont donc hébergés dans un processus séparé : le **Serveur MCP** (`mcp_tools_swebench.py` ou `mcp_tools_mbpp.py`).

### La question clé :
> *Comment le code Python du LLM peut-il appeler `read_file(path="src/main.py")` dans la Sandbox alors que la Sandbox n'a pas accès au disque ?*

C'est là qu'interviennent les **fonctions wrappers** fabriquées par le **Bridge** (`src/mcp/bridge.py`).

---

## 2. Vue d'Ensemble des Composants

```text
┌─────────────────────────────────────────────────────────────┐
│ 1. Code du LLM dans la Sandbox                              │
│    texte = read_file(path="src/main.py")                    │
└──────────────────────────────┬──────────────────────────────┘
                               │ Appel local
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Fonction Wrapper (dans sandbox_globals)                  │
│    - Reçoit path="src/main.py" via **kwargs                 │
│    - Sait qu'elle s'appelle "read_file"                     │
│    - Appelle mcp_client.call_tool("read_file", kwargs)      │
└──────────────────────────────┬──────────────────────────────┘
                               │ Appel Python interne
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Client MCP (MCPClient)                                   │
│    - Formate la requête en JSON-RPC 2.0                     │
│    - Envoie la trame sur stdin du serveur                   │
└──────────────────────────────┬──────────────────────────────┘
                               │ Tube OS (stdin / stdout)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Serveur MCP (Processus mcp_tools_swebench.py)            │
│    - Exécute le VRAI code (src/tools/file_tools.py)         │
│    - Lit le fichier, formate les lignes (cat -n)            │
│    - Renvoie la réponse JSON-RPC 2.0 sur stdout             │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Le Code du Wrapper dans `src/mcp/bridge.py`

Le Bridge ne code pas chaque outil à la main. Il utilise le patron de conception **Fabrique** (*Factory*) avec une fonction `build_wrapper` :

```python
import asyncio
from typing import Any, Callable
from src.mcp.client import MCPClient


class MCPToolBridge:
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client

    def build_wrapper(self, tool_name: str) -> Callable[..., Any]:
        """Fabrique une fonction enveloppe (wrapper) sur-mesure pour un outil."""

        def wrapper(**kwargs: Any) -> Any:
            """Ce code s'exécute quand le LLM appelle l'outil dans la Sandbox."""
            # 1. On relaie l'appel au client MCP avec les arguments reçus
            result = asyncio.run(
                self.mcp_client.call_tool(name=tool_name, arguments=kwargs)
            )
            # 2. On retourne la valeur au code du LLM
            return result

        wrapper.__name__ = tool_name
        return wrapper
```

---

## 4. Exemple Pas-à-Pas : Appel à `read_file`

Suivons précisément la circulation de l'information lors de l'exécution de :
```python
texte = read_file(path="src/main.py")
```

### Étape 0 : Préparation au démarrage (La mise en place)
Avant d'exécuter le moindre code du LLM :
1. Le client MCP découvre les outils disponibles sur le serveur (dont `"read_file"`).
2. Le Bridge fabrique le wrapper dédié : `wrapper_read_file = bridge.build_wrapper("read_file")`.
3. Le dictionnaire de la Sandbox est préparé :
   ```python
   sandbox_globals = {
       "read_file": wrapper_read_file,
       "__builtins__": builtins_securises,
   }
   ```

---

### Étape 1 : Déclenchement par le code du LLM
La Sandbox lance l'exécution :
```python
exec('texte = read_file(path="src/main.py")', sandbox_globals)
```
Python analyse la ligne, cherche le mot `read_file` dans `sandbox_globals`, et trouve la fonction **`wrapper`**. Il l'exécute.

---

### Étape 2 : Que se passe-t-il PRÉCISÉMENT dans le Wrapper ?

Le wrapper prend le contrôle :

```python
def wrapper(**kwargs):
    # 2.1. Capture des arguments :
    # kwargs vaut automatiquement : {"path": "src/main.py"}

    # 2.2. Mémoire interne (Closure) :
    # Le wrapper sait qu'il est associé à tool_name = "read_file"
    # et connaît la référence vers self.mcp_client

    # 2.3. Délégation au client :
    result = self.mcp_client.call_tool(name="read_file", arguments=kwargs)

    # 2.4. Retour du résultat :
    return result
```

1. **Capture flexible (`**kwargs`)** : Quels que soient les arguments passés par le LLM, Python les regroupe dans un dictionnaire `kwargs`.
2. **Interception silencieuse** : Le wrapper ne lit aucun fichier lui-même ; il met l'exécution de la Sandbox en pause et passe la main au client MCP.

---

### Étape 3 : Le Client MCP émet la requête JSON-RPC
Le `MCPClient` reçoit `name="read_file"` et `arguments={"path": "src/main.py"}`.
Il sérialise l'appel selon le protocole officiel **JSON-RPC 2.0** :
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "read_file",
    "arguments": {
      "path": "src/main.py"
    }
  }
}
```
Il écrit cette ligne sur le tube d'entrée standard (`sys.stdin`) du serveur MCP.

---

### Étape 4 : Le Serveur MCP exécute le vrai code
Le processus serveur (`mcp_tools_swebench.py`) lit la ligne sur son `stdin` :
1. Il identifie la méthode `read_file`.
2. Il exécute la fonction métier sous-jacente (`src/tools/file_tools.py`) :
   * Vérification des droits d'accès au répertoire `/testbed`.
   * Lecture réelle du fichier sur le disque ou dans le conteneur Docker.
   * Ajout du préfixe des numéros de lignes (`cat -n`).
3. Il renvoie le résultat en JSON-RPC sur son `sys.stdout` :
   ```json
   {
     "jsonrpc": "2.0",
     "id": 1,
     "result": {
       "content": [
         {
           "type": "text",
           "text": "1: \"\"\"Application main entry point...\"\"\"\n2: import sys\n..."
         }
       ]
     }
   }
   ```

---

### Étape 5 : Réception et déballage dans le Wrapper
1. `MCPClient` lit la réponse sur le `stdout` du serveur.
2. Il extrait le texte brut : `"1: \"\"\"Application main entry point...\"\"\"\n..."`.
3. La méthode `call_tool()` se termine et retourne cette chaîne.
4. Le **wrapper** sort de sa pause et exécute son `return result`.

---

### Étape 6 : Affectation finale dans la Sandbox
* Dans le code du LLM, l'expression `read_file(path="src/main.py")` est remplacée par la chaîne retournée.
* La variable `texte` reçoit le contenu du fichier.
* L'exécution du code du LLM se poursuit vers la ligne suivante.

---

## 5. Synthèse des Bénéfices Architecturaux

| Concept | Pourquoi cette approche ? |
|---|---|
| **Sécurité étanche** | Le code non fiable du LLM ne dispose d'aucun descripteur de fichier ni d'accès disque dans la Sandbox. Tout accès passe par le serveur MCP qui valide les règles. |
| **Transparence pour le LLM** | Le LLM écrit du Python naturel (`read_file(...)`) sans avoir à se soucier du réseau ou de JSON-RPC. |
| **Généricité totale (*Factory*)** | `build_wrapper` s'adapte automatiquement à n'importe quel nombre d'outils exposés par le serveur sans modification de code. |
