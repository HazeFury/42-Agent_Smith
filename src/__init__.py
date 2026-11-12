"""Package racine du projet Agent Smith.

Ce package regroupe l'ensemble des modules sources du framework agentique :
- models : Modèles de données Pydantic v2 (contrats stricts).
- core   : Moteur agentique agnostique (boucle ReAct, prompts, extraction).
- agent  : Orchestrateurs applicatifs spécifiques (MBPP et SWE-bench).
- sandbox: Environnement d'exécution sécurisé et isolé.
- mcp    : Client Model Context Protocol et injection dynamique d'outils.
- llm    : Abstraction multi-fournisseurs, gestion des quotas et rotation.
- tools  : Implémentation des outils métiers filesystem, recherche et
           exécution.
"""
