# Les résultats

Tout ce que le service produit s'écrit ici. Le dossier est **vide dans le dépôt** : il se remplit quand on lance le service, et son contenu n'est pas versionné.

| Élément | À quoi il sert |
| --- | --- |
| [`corpus/`](corpus/) | chaque version du corpus, une fois contrôlée par le service : `kit importer` |
| [`reponses_du_rag/`](reponses_du_rag/) | ce que le RAG a rendu par ses endpoints, une version du RAG par dossier : `kit appeler-rag` ou `kit evaluer` |
| [`evaluations/`](evaluations/) | **une évaluation par configuration** du RAG, avec son `RAPPORT.md` : `kit evaluer` |
| [`comparaisons_de_configurations/`](comparaisons_de_configurations/) | **deux configurations comparées**, avec leur `RAPPORT.md` : `kit comparer` |
| `base.sqlite` | la base de données du service : tout, y compris le détail des questions réservées |

Les mêmes dossiers, remplis : [`service-evaluation-exemple/resultats/`](../../service-evaluation-exemple/resultats/).
