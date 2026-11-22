"""Le pipeline du RAG, une étape par fichier, dans l'ordre où elles s'enchaînent.

etape_1_extraction  → lire les documents
etape_2_decoupage   → les couper en chunks qui portent leurs métadonnées
etape_3_index       → rendre les chunks cherchables (sens et mots)
etape_4_graphe      → extraire un graphe des chunks (optionnelle : avec elle, le RAG est « hybride »)
etape_5_recherche   → trouver les meilleurs chunks pour une question
etape_6_generation  → rédiger une réponse citée, ou s'abstenir
"""
