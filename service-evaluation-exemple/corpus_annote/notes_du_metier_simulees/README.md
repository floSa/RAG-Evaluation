# Les notes du métier, simulées

Dans un vrai projet, le métier remplit lui-même les fichiers Excel que le service lui prépare : `verification_juge.xlsx`, pour vérifier le juge, et `relecture_reponses.xlsx`, pour relire les réponses de chaque évaluation. Ici, l'entreprise est fictive : Claude a joué le rôle du métier, et ses notes sont écrites dans ce dossier, chacune avec sa raison. Aucun avis métier réel.

| Élément | À quoi il sert |
| --- | --- |
| [`verdicts_metier.json`](verdicts_metier.json) | 28 réponses du RAG notées juste, partielle ou fausse : elles servent à vérifier le modèle juge |
| [`relectures_metier.json`](relectures_metier.json) | pour chacune des trois évaluations, les réponses à relire : d'accord ou non avec la note du juge, et sinon la note du métier, avec sa raison |
| [`publier.py`](publier.py) | écrit ces notes dans `verification_juge.xlsx` et dans les `relecture_reponses.xlsx`, comme le métier les aurait remplis |
