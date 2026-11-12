"""Package des tests unitaires et d'intégration du projet Agent Smith.

Ce dossier regroupe les suites de validation automatisées :
- test_sandbox_security.py : Vérification rigoureuse des verrous du sandbox
                             (blocage imports, builtins, paths, quotas RAM,
                             timeouts, réseau) pour garantir 100% sur
                             exam_sandbox.sh.
- test_code_extractor.py   : Validation de l'extraction de code multi-formats
                             (Markdown Python, XML Anthropic, JSON Hermes,
                             ReAct).
- test_llm_rotation.py     : Tests de rotation automatique des clés d'API et
                             résilience aux erreurs HTTP 429.
- test_mcp_tools.py        : Tests unitaires indépendants des 9 outils
                             obligatoires (filesystem, search, execution).
- test_mbpp_loop.py        : Test d'intégration bout-en-bout de la boucle
                             ReAct sur une tâche MBPP synthétique.
- test_swebench_patch.py   : Vérification de la validité du format git diff
                             généré pour SWE-bench.
"""
