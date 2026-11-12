"""Package des modèles de données Pydantic v2.

Ce dossier contient les contrats de données stricts imposés par le sujet :
- config.py  : Modèle SandboxConfig (allowlists d'imports avec wildcards,
               répertoires autorisés, quotas mémoire et timeouts).
- tasks.py   : Modèles d'entrée d'évaluation (MBPPTaskInput,
               SWEBenchTaskInput).
- metrics.py : Modèles d'évaluation et de journalisation (StepMetrics,
               SolutionOutput pour le fichier solution.json).

Ces modèles garantissent la validation stricte des entrées/sorties et la
conformité aux exigences de la moulinette.
"""
