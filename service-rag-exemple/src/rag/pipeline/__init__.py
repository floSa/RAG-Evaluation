"""Le pipeline du RAG, une étape par fichier, dans l'ordre où elles s'enchaînent.

etape_1_extraction  → lire les documents
etape_2_decoupage   → les couper en chunks qui portent leurs métadonnées
etape_3_index       → rendre les chunks cherchables (sens et mots)
etape_4_recherche   → trouver les meilleurs chunks pour une question, par le sens et par les mots
etape_5_generation  → rédiger une réponse citée, ou s'abstenir
"""
