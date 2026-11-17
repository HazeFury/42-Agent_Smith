# Logger

Ce guide explique à l'équipe comment utiliser le système de journalisation (`logging`) dans l'ensemble du projet.

---

## Toujours `sys.stderr`, JAMAIS `print()`

> [!CAUTION]
> **Ne jamais utiliser `print()` pour afficher des messages de débogage ou d'information dans le code.**
> La moulinette d'évaluation et le protocole MCP en mode `stdio` utilisent le flux standard `sys.stdout` pour échanger du JSON pur.
> Si vous utilisez un `print()`, vous polluez `stdout`, le JSON sera corrompu et la tâche échouera immédiatement avec une note de zéro.

Notre logger est spécialement configuré pour envoyer **100% des messages sur `sys.stderr`**, protégeant ainsi l'évaluation tout en garantissant un affichage propre dans votre terminal.

---

## 1. Comment utiliser le logger dans vos fichiers ?
*(Modules, Serveurs MCP, Sandbox, Orchestrateur, Points d'entrée CLI, etc.)*

Dans **tous** les fichiers du projet sans exception, vous n'avez que **2 lignes** à écrire tout en haut de votre fichier :

```python
from src.core.logger import get_logger

# Instancie le logger propre à ce fichier grâce à __name__
logger = get_logger(__name__)
```

Ensuite, utilisez simplement `logger` dans vos fonctions et classes :

```python
class FileSystemGuard:
    def safe_open(self, filepath: str):
        logger.debug(f"Vérification des permissions pour : {filepath}")

        if not self.is_authorized(filepath):
            logger.warning(f"Tentative d'accès non autorisé : {filepath}")
            raise PermissionError("Accès refusé")

        logger.info(f"Fichier ouvert avec succès : {filepath}")
```

### Format du log produit automatiquement :
```text
11:15:32 | INFO    | agent_smith.sandbox.fs_guard | Fichier ouvert avec succès : /testbed/file.py
```
👉 On sait immédiatement **à quelle heure**, avec **quel niveau de sévérité**, et **dans quel fichier précis** l'événement s'est produit.

---

## 2. Quels niveaux de log utiliser ?

Utilisez le bon niveau selon la situation :

| Méthode | Quand l'utiliser ? | Exemple |
|---|---|---|
| `logger.debug(...)` | Détails très verbeux utiles uniquement pendant le dev local | Inspection d'un token, payload JSON brut, variables d'étape. |
| `logger.info(...)` | Événement normal confirmant le bon fonctionnement | Démarrage d'une itération, outil MCP appelé, fin de tâche. |
| `logger.warning(...)` | Comportement inhabituel ou contournement, sans arrêt du programme | Retry après une erreur 429, bloc de code malformé mais rattrapé. |
| `logger.error(...)` | Échec ou erreur sur une opération | Fichier introuvable, timeout d'exécution sandbox atteint. |
| `logger.exception(...)` | Dans un bloc `except` pour afficher l'erreur **avec la stack trace complète** | Capture d'une exception inattendue. |

### Exemple avec `logger.exception()` :
```python
try:
    result = execute_code(snippet)
except Exception as e:
    # Affiche le message ET toute la pile d'appels sans faire crasher l'agent
    logger.exception(f"Erreur inattendue pendant l'exécution : {e}")
```

---

## 3. Les points d'entrée CLI
*(`src/main.py`, `agent_mbpp.py`, `agent_swebench.py`, `src/sandbox/cli.py`)*

Les scripts exécutables au lancement n'ont **aucune configuration spécifique à faire**.
Grâce à l'auto-initialisation du logger, ils s'utilisent exactement comme n'importe quel autre module :

```python
import sys
from src.core.logger import get_logger
from src.core.exceptions import AgentSmithException

logger = get_logger(__name__)

def main():
    logger.info("Lancement de l'agent...")
    # ... reste du code ...

if __name__ == "__main__":
    main()
```

> [!NOTE]
> `get_logger(__name__)` initialise automatiquement et de façon transparente le système de logging parent `agent_smith` sur `sys.stderr` au niveau `INFO` dès son tout premier appel.

---

## 4. Et si je suis dans un test unitaire `pytest` ?

**Toujours rien de spécial à faire !**
Comme pour le reste du code, le premier appel à `get_logger(__name__)` dans un test ou dans le code testé déclenche automatiquement l'initialisation sur `sys.stderr`.

---

## 5. Résumé des Bonnes et Mauvaises Pratiques

| ❌ À PROSCRIRE | ✅ BONNE PRATIQUE |
|---|---|
| `print("Erreur:", err)` | `logger.error(f"Erreur: {err}")` |
| `logger = logging.getLogger("mon_nom")` | `logger = get_logger(__name__)` |
| Écrire des logs sur `sys.stdout` | Toujours diriger vers `sys.stderr` |
| Configurer manuellement les handlers | Laisser `get_logger(__name__)` s'auto-initialiser |
