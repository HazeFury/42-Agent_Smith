"""Package de l'environnement d'exécution sécurisé et isolé.

Ce dossier implémente les mécanismes d'isolation et de sécurité imposés par le
sujet (Section V.2 et script exam_sandbox.sh) sans aucune bibliothèque
externe :
- core.py           : SandboxRunner, exécution de code dans un sous-processus
                      isolé et injection de la primitive native final_answer().
- security.py       : ASTSecurityAnalyzer, analyse statique AST pour bloquer
                      les imports interdits et attributs dunder suspects.
- builtins_guard.py : Assainissement du dictionnaire __builtins__ (retrait de
                      eval, exec, compile, etc.).
- fs_guard.py       : Wrapper sécurisé open() résolvant les chemins canoniques
                      (realpath) et restreignant l'accès aux
                      allowed_directories.
- limits.py         : Contrôle des ressources Linux (resource.setrlimit pour la
                      RAM, timeouts stricts et coupure réseau).
- cli.py            : Mode REPL interactif en ligne de commande pour la
                      commande 'uv run sandbox'.
"""
