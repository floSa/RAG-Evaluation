# Les six étapes du RAG

| Élément | À quoi il sert |
| --- | --- |
| [`etape_1_extraction.py`](etape_1_extraction.py) | lire les documents, les scans et les tableaux, avec Docling |
| [`etape_2_decoupage.py`](etape_2_decoupage.py) | découper en morceaux de texte, section par section |
| [`etape_3_index.py`](etape_3_index.py) | rendre les morceaux cherchables, par le sens (vecteurs) et par les mots |
| [`etape_4_recherche.py`](etape_4_recherche.py) | retrouver les k morceaux les plus utiles, en écartant les documents interdits |
| [`etape_5_generation.py`](etape_5_generation.py) | faire écrire la réponse, avec ses sources |

Comment chaque étape est construite : [Guide du RAG d'exemple](../../../documentation/guide_du_rag.md).
