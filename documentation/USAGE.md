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

## 1. Comment utiliser le logger dans un module classique ?
*(Sandbox, Serveur MCP, Outils, Orchestrateur, LLM Providers, etc.)*

Dans 99% des cas, vous êtes dans un fichier de code interne. Vous n'avez que **2 lignes** à écrire tout en haut de votre fichier :

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

## 3. Comment configurer les points d'entrée CLI ?
*(Uniquement dans `src/main.py`, `agent_mbpp.py`, `agent_swebench.py`, `src/sandbox/cli.py`)*

Les points d'entrée sont les scripts exécutables au lancement. Ce sont les **seuls** fichiers du projet qui doivent appeler `setup_agent_logging()` :

```python
import sys
from src.core.logger import setup_agent_logging, get_logger

def main():
    # 1. On initialise le parent 'agent_smith' sur sys.stderr une seule fois
    setup_agent_logging(level="INFO")  # ou "DEBUG" si option verbeuse

    # 2. On prend le logger de ce fichier
    logger = get_logger(__name__)
    logger.info("Lancement de l'agent...")

    # ... reste du code ...

if __name__ == "__main__":
    main()
```

---

## 4. Et si je suis dans un test unitaire `pytest` ?

**Rien à faire !**
Le module `logger.py` intègre une auto-initialisation paresseuse (*lazy loading*). Si vous écrivez un test dans `tests/test_something.py` sans passer par `main.py`, le premier appel à `get_logger(__name__)` détectera l'absence de configuration et initialisera automatiquement le logger par défaut sur `sys.stderr`.

---

## 5. Résumé des Bonnes et Mauvaises Pratiques

| ❌ À PROSCRIRE | ✅ BONNE PRATIQUE |
|---|---|
| `print("Erreur:", err)` | `logger.error(f"Erreur: {err}")` |
| `logger = logging.getLogger("mon_nom")` | `logger = get_logger(__name__)` |
| Écrire des logs sur `sys.stdout` | Toujours diriger vers `sys.stderr` |
| Appeler `setup_agent_logging()` dans un module métier | Appeler `setup_agent_logging()` uniquement dans les points d'entrée CLI |
