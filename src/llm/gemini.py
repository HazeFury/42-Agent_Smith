# Certains acteurs ont refusé d'adopter le format OpenAI et ont créé leur propre structure JSON. C'est le cas de Google Gemini :

# json
# {
#   "candidates": [
#     {
#       "content": {
#         "parts": [{ "text": "Voici le code..." }]   <-- Chemin différent !
#       }
#     }
#   ],
#   "usageMetadata": {
#     "promptTokenCount": 142,                       <-- Noms de clés différents !
#     "candidatesTokenCount": 58
#   }
# }
