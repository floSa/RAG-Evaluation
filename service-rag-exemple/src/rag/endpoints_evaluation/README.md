# Les endpoints d'évaluation

Les quatre adresses web que le service d'évaluation appelle. Si on supprime ce dossier, le RAG marche toujours.

| Élément | À quoi il sert |
| --- | --- |
| [`adresse_web.py`](adresse_web.py) | ouvre les quatre endpoints à http://127.0.0.1:8100 |
| [`ingerer.py`](ingerer.py) | ① reçoit les documents de l'évaluation, et les range à part de son propre corpus documentaire |
| [`montrer_index.py`](montrer_index.py) | ② rend la version du RAG, ses morceaux de texte, les pages lues |
| [`rechercher.py`](rechercher.py) | ③ rend les k morceaux retrouvés pour une question |
| [`repondre.py`](repondre.py) | ④ rend la réponse, ses sources, et s'il s'abstient |

La règle que chaque RAG doit suivre : [0b. Les endpoints du RAG : ce que chaque RAG doit fournir](../../../../service-evaluation/documentation/0b_endpoints_du_rag.md).
