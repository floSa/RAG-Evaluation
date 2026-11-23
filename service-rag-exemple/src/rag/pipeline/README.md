# Les six étapes du RAG

| Élément | À quoi il sert |
| --- | --- |
| [`etape_1_extraction.py`](etape_1_extraction.py) | lire les documents, les scans et les tableaux, avec Docling |
| [`etape_2_decoupage.py`](etape_2_decoupage.py) | découper en morceaux de texte, section par section |
| [`etape_3_index.py`](etape_3_index.py) | ranger les morceaux dans la base vectorielle |
| [`etape_4_graphe.py`](etape_4_graphe.py) | facultatif : extraire le graphe des liens entre équipements, sites et personnes |
| [`etape_5_recherche.py`](etape_5_recherche.py) | retrouver les k morceaux les plus utiles, en écartant les documents interdits |
| [`etape_6_generation.py`](etape_6_generation.py) | faire écrire la réponse, avec ses sources |

Comment chaque étape est construite : [Guide du RAG d'exemple](../../../documentation/guide_du_rag.md).
