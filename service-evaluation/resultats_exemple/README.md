# Résultats d'exemple

Ce dossier montre ce que produit le service d'évaluation, sans rien lancer. Il a évalué le RAG d'exemple ([`service-rag/`](../../service-rag/)) sur le corpus d'exemple : 50 documents fictifs de maintenance électrique, et 60 questions écrites par le métier avec leur bonne réponse. 40 questions servent à régler le RAG ; 20 sont réservées à la décision.

Le service fait **deux choses différentes**, rangées dans deux dossiers :

- **Évaluer une configuration** ([`evaluations/`](evaluations/)). Une configuration, c'est le RAG avec tous ses réglages fixés : nombre de morceaux ramenés (k), modèles, prompt, graphe ou non. L'évaluation répond à une question : *cette configuration peut-elle partir en production ?*
- **Comparer deux configurations** ([`comparaisons/`](comparaisons/)), déjà évaluées sur les mêmes questions. La comparaison répond à une autre question : *laquelle fait mieux, et l'écart est-il réel ou dû au hasard ?*

Chaque dossier contient un `RAPPORT.md`, à lire directement ici, et un dossier `donnees/` avec les fichiers techniques dont il est tiré. On n'ouvre ces fichiers que pour creuser.

## 1. Quatre configurations évaluées

Commencer par la référence.

| Configuration | Ce qui la distingue de la référence | Score pondéré | Décision | Rapport |
| --- | --- | --- | --- | --- |
| **Référence** | RAG vectoriel, 5 morceaux ramenés par question | 80 % | ❌ non recommandée : 1 erreur grave | [lire](evaluations/reference/RAPPORT.md) |
| k = 3 | 3 morceaux ramenés au lieu de 5 | 77 % | ❌ non recommandée | [lire](evaluations/k3/RAPPORT.md) |
| Sans réflexion | le modèle répond sans « réfléchir » d'abord | 77 % | ❌ non recommandée | [lire](evaluations/sans_reflexion/RAPPORT.md) |
| Hybride | un graphe ajouté aux morceaux de texte | 82 % | ❌ non recommandée | [lire](evaluations/hybride/RAPPORT.md) |

Le **score pondéré** est la part de réponses justes, où chaque question compte selon sa fréquence et sa gravité. C'est le chiffre le plus proche de ce que vivront les utilisateurs.

**Aucune configuration n'est prête.** Les quatre butent sur les mêmes points : les pages scannées sont mal lues (15 % de caractères faux, pour un seuil de 2 %), et la recherche ne ramène pas assez souvent le bon passage (moins de 90 %).

## 2. Trois comparaisons avec la référence

| Comparaison | Ce qu'on en conclut | Rapport |
| --- | --- | --- |
| Référence contre **k = 3** | **Pas meilleure.** Elle ramène moins souvent le bon passage (75 % contre 86 %), et perd 4 questions sans en gagner aucune. Elle n'a plus d'erreur grave, mais seulement parce qu'elle se tait sur la question en cause (Q-046). | [lire](comparaisons/reference_contre_k3/RAPPORT.md) |
| Référence contre **sans réflexion** | **On garde la réflexion.** Sans elle, le RAG répond 9 fois plus vite (0,9 s contre 7,4 s), mais calcule mal : 75 % de chiffres exacts contre 91 %. Avec la réflexion, 7,4 s reste sous le seuil de 15 s. | [lire](comparaisons/reference_contre_sans_reflexion/RAPPORT.md) |
| Référence contre **hybride** | **Rien de mesurable.** Le graphe fait gagner 2 questions et en perdre 1 : l'écart peut venir du hasard. Ce corpus a peu de questions qui demandent de suivre des liens entre documents. | [lire](comparaisons/reference_contre_hybride/RAPPORT.md) |

## 3. Ce que vérifie chaque évaluation

Chaque rapport d'évaluation donne les scores de quatre évaluations, dans cet ordre :

1. **Ingestion** : le service d'ingestion n'a rien perdu ni abîmé en découpant les documents, en les vectorisant et en les rangeant dans la base vectorielle. Détail : [guide 1](../documentation/1_evaluation_ingestion.md).
2. **Recherche** : pour chaque question, la recherche ramène les morceaux qui contiennent la réponse, et jamais un document interdit à la personne qui pose la question. Détail : [guide 2](../documentation/2_evaluation_recherche.md).
3. **Réponse** : la réponse est juste, ne dit que ce que disent les documents, et le RAG sait dire « je ne sais pas ». Détail : [guide 3](../documentation/3_evaluation_reponse.md).
4. **Bout en bout** : le RAG est bon sur les questions qui comptent le plus, assez rapide et pas trop cher. Détail : [guide 4](../documentation/4_evaluation_bout_en_bout.md).

Vos propres évaluations s'écrivent au même format dans [`sorties/`](../sorties/) : `resultats/` pour les évaluations, `comparaisons/` pour les comparaisons.
