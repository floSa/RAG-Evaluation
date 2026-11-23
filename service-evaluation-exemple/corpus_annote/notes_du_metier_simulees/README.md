# Les notes du métier, simulées

Dans un vrai projet, le métier note lui-même, dans les fichiers Excel que le service lui prépare : `verification_juge.xlsx` pour les réponses du RAG, `justesse_graphe.xlsx` pour les relations du graphe. Ici, l'entreprise est fictive : Claude a joué le rôle du métier, et ses notes sont écrites dans ces fichiers, chacune avec sa raison. Aucun avis métier réel.

| Élément | À quoi il sert |
| --- | --- |
| [`verdicts_metier.json`](verdicts_metier.json) | 28 réponses du RAG notées juste, partielle ou fausse : elles servent à vérifier le modèle juge |
| [`justesse_graphe.json`](justesse_graphe.json) | 50 relations du graphe jugées justes ou fausses |
| [`publier.py`](publier.py) | écrit ces notes dans les fichiers `verification_juge.xlsx` et `justesse_graphe.xlsx`, comme le métier les aurait remplis |
