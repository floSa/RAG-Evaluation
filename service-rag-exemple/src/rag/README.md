# Le code de la commande `rag`

| Élément | À quoi il sert |
| --- | --- |
| [`pipeline/`](pipeline/) | le RAG lui-même, en six étapes |
| [`endpoints_evaluation/`](endpoints_evaluation/) | les quatre endpoints ouverts au service d'évaluation : la seule partie écrite pour l'évaluation |
| [`assistant.py`](assistant.py) | enchaîne les étapes du RAG |
| [`commandes.py`](commandes.py) | les commandes `rag …` : indexer, demander, ouvrir les endpoints |
