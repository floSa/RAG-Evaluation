# La méthode et le contrat

Les textes de fond. Les guides les citent par numéro : « document 1 », « document 3 ».

| Élément | À quoi il sert |
| --- | --- |
| [`methode_corpus_annote.md`](methode_corpus_annote.md) | **document 1** : comment constituer le corpus annoté |
| [`methode_evaluation.md`](methode_evaluation.md) | **document 3** : la méthode d'évaluation, les quatre évaluations, chaque score, les scores clés lus par le métier |
| [`contrat_des_fichiers.md`](contrat_des_fichiers.md) | le format exact de chaque fichier échangé entre le service et un RAG, champ par champ |
| [`prompt_du_juge.md`](prompt_du_juge.md) | le prompt du modèle juge, sa sortie, et comment on le vérifie |
| [`schemas/`](schemas/) | le contrat, sous forme de schémas que le service utilise pour vérifier les fichiers |
| [`images/`](images/) | les illustrations des documents 1 et 3 |

Le document 2, sur les techniques d'un RAG, est avec le RAG d'exemple : [`service-rag-exemple/documentation/reference/techniques_rag.md`](../../../service-rag-exemple/documentation/reference/techniques_rag.md).

**Attention** : `schemas/` et `prompt_du_juge.md` sont lus par le code du service. Les modifier change l'évaluation.
