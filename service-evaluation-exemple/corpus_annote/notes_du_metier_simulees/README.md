# Les notes du métier, simulées

Dans un vrai projet, le métier note lui-même dans Langfuse. Ici, l'entreprise est fictive : Claude a joué le rôle du métier, et ses notes sont écrites dans ces fichiers, chacune avec sa raison. Aucun avis métier réel.

| Élément | À quoi il sert |
| --- | --- |
| [`verdicts_metier.json`](verdicts_metier.json) | 28 réponses du RAG notées juste, partielle ou fausse : elles servent à vérifier le modèle juge |
| [`justesse_graphe.json`](justesse_graphe.json) | 50 relations du graphe jugées justes ou fausses |
| [`publier.py`](publier.py) | inscrit ces notes dans Langfuse, comme le métier l'aurait fait |
