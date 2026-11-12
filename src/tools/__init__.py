"""Package des implémentations concrètes des outils métiers.

Ce dossier regroupe les outils exposés par les serveurs MCP (Section V.5) :
- file_tools.py      : Outils de manipulation de fichiers (read_file au format
                       'cat -n', edit_file par remplacement exact, list_files).
- search_tools.py    : Outils d'exploration du code source (search_code type
                       grep, search_function_or_class_definition_in_code,
                       find_references).
- execution_tools.py : Outils d'exécution système (run_tests pour lancer
                       l'évaluation, run_command pour bash, get_patch pour
                       générer le diff unifié via
                       'git -c core.fileMode=false diff').
- mbpp_tools.py      : MBPPToolKit implémentant l'outil d'évaluation
                    algorithmique
                       run_tests(code, test_list).
- docker_manager.py  : Gestionnaire du conteneur Docker SWE-bench (démarrage,
                       résolution de TESTBED_PATH, et nettoyage garanti sur
                       signal SIGTERM).
"""
