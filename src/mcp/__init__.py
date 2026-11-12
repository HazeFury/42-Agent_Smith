"""Package du client Model Context Protocol (MCP) et dynamic bridge.

Ce dossier implémente l'intégration du standard MCP requise par le sujet
(Section V.2.4 et V.5) :
- client.py         : MCPClient, client gérant les connexions aux serveurs MCP
                      via les transports 'stdio' et 'streamable HTTP (SSE)'.
- dynamic_manual.py : Générateur dynamique du manuel textuel d'outils injecté
                      dans le prompt de l'agent à partir des schémas d'outils
                      découverts.
- bridge.py         : Bridge transformant dynamiquement les outils MCP distants
                      en fonctions Python appelables directement dans le
                      namespace du sandbox.
"""
