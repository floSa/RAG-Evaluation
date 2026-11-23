# Résultats d'exemple

Ce dossier montre **à quoi ressemblent les résultats d'une évaluation**, sans rien lancer. Ce sont les quatre évaluations du RAG d'exemple ([`service-rag/`](../../service-rag/)) sur le corpus d'exemple, celles que citent les guides.

Ouvrir d'abord **`rapport.html`** de l'évaluation de référence, dans un navigateur : c'est la page que lit le métier.

| Évaluation | Ce qui change | Score pondéré | Décision | Cité dans |
| --- | --- | --- | --- | --- |
| [`2026-11-20.1_graphrag-vectoriel-k5-5954e822`](2026-11-20.1_graphrag-vectoriel-k5-5954e822/rapport.html) | **la référence** : RAG vectoriel, k = 5 | 80 % | non recommandée (1 erreur grave) | guides 1 à 5 |
| [`2026-11-20.1_graphrag-vectoriel-k3-5954e822`](2026-11-20.1_graphrag-vectoriel-k3-5954e822/rapport.html) | k = 3 au lieu de 5 | 77 % | non recommandée | [guide 5](../documentation/5_resultats_et_comparaison.md#5-comparer-deux-versions) |
| [`2026-11-20.1_graphrag-hybride-k5-57001489`](2026-11-20.1_graphrag-hybride-k5-57001489/rapport.html) | le graphe ajouté aux chunks (RAG hybride) | 82 % | non recommandée | [guide 5](../documentation/5_resultats_et_comparaison.md#5-comparer-deux-versions) |
| [`2026-11-20.1_graphrag-vectoriel-k5-94d362c8`](2026-11-20.1_graphrag-vectoriel-k5-94d362c8/rapport.html) | génération sans réflexion | 77 % | non recommandée | [guide 5](../documentation/5_resultats_et_comparaison.md#5-comparer-deux-versions) |

Le rôle de chaque fichier d'un dossier : [guide 5, « Où sont les résultats »](../documentation/5_resultats_et_comparaison.md#1-où-sont-les-résultats). Les fichiers `comparaison_avec_….json` sont ceux de `kit comparer`.

Ce dossier est une **copie figée**. Vos propres évaluations s'écrivent dans [`sorties/resultats/`](../sorties/), qui reste vide dans le dépôt. Les liens vers Langfuse (`langfuse.json`) ne marchent que sur la machine qui a fait l'évaluation.
