"""Package des orchestrateurs applicatifs spécialisés par benchmark.

Ce dossier contient les agents dédiés à chaque évaluation du sujet 42 :
- mbpp_agent.py     : MBPPAgent, orchestrateur dédié à la résolution des tâches
                      algorithmiques MBPP (chargement tâche, limites 10 iters /
                      120s / 6k tokens, écriture du code Python dans
                      solution.json).
- swebench_agent.py : SWEBenchAgent, orchestrateur dédié à la résolution des
                      tâches SWE-bench (gestion du cycle de vie Docker, limites
                      30 iters / 900s / 300k tokens, génération et écriture du
                      patch git diff dans solution.json).
"""
