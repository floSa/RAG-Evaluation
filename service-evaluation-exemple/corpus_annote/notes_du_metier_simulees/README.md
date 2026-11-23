# Les notes du métier, simulées

Dans un vrai projet, le métier note lui-même les réponses du RAG, dans le fichier Excel `verification_juge.xlsx` que le service lui prépare. Ici, l'entreprise est fictive : Claude a joué le rôle du métier, et ses notes sont écrites dans ce dossier, chacune avec sa raison. Aucun avis métier réel.

| Élément | À quoi il sert |
| --- | --- |
| [`verdicts_metier.json`](verdicts_metier.json) | 28 réponses du RAG notées juste, partielle ou fausse : elles servent à vérifier le modèle juge |
| [`publier.py`](publier.py) | écrit ces notes dans le fichier `verification_juge.xlsx`, comme le métier l'aurait rempli |
