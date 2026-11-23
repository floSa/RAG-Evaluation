# 6. Aide à la décision : lire les scores

Ce guide détaille la décision de l'étape 4 du [fil conducteur](../FIL_CONDUCTEUR.md#4-lire-le-rapport-comparer-faire-décider-le-métier). Il s'adresse à la personne qui présente les scores à ceux qui décident : le métier, pour la mise en production ; l'équipe du RAG, pour choisir une configuration ou garder une amélioration.

Le service ne fixe aucun seuil : un score vaut ce que vaut l'usage qu'on fait du RAG. Ce guide donne des **repères**, à adapter à chaque application avec le métier, et la façon de lire la précision de chaque score.

## 1. Les repères, score par score

Les noms sont ceux des scores clés du rapport. Un score « en dessous du repère » n'interdit rien : il dit où regarder, et ce que ça coûtera aux utilisateurs.

| Score | Repère | En dessous, ce que ça veut dire |
| --- | --- | --- |
| Documents présents dans la base | 100 % | un document entier n'a pas été lu : le RAG ne peut rien répondre de ce qu'il contient |
| Étiquettes complètes | 100 % | des morceaux de texte ont perdu leur source ou leurs droits d'accès : le RAG ne peut ni les citer, ni les filtrer |
| Passages du métier retrouvés | 95 % | des réponses sont perdues dès la lecture des documents : aucun réglage de la recherche ne les retrouvera |
| Erreur de lecture des scans | 2 caractères sur 100, au plus | au-delà, des chiffres et des références sont mal lus sur les pages scannées |
| Bon passage ramené | 90 % | la recherche ne donne pas au modèle le texte qui contient la réponse : il répond à côté, ou dit qu'il ne sait pas |
| Fuites de droits | 0 | **une seule est un problème de sécurité**, quel que soit le reste : un document a été montré à qui n'y a pas droit |
| Réponses justes | 80 % | une réponse sur cinq, ou plus, est fausse ou incomplète. À lire avec l'état du juge, en tête du rapport : s'il n'est pas validé, ce score est incertain |
| Sait dire « je ne sais pas » | 80 % | quand la réponse n'est pas dans les documents, le RAG invente au lieu de le dire |
| Fidélité aux documents | 90 % | les réponses contiennent des affirmations qui ne sont pas dans les documents ramenés |
| Erreurs graves | 0 | **chacune se regarde avant tout le reste** : une réponse fausse ou inventée, sur une question où l'erreur a des conséquences graves |
| Score pondéré | 80 % | les réponses sont moins bonnes sur les questions fréquentes ou graves, celles qui comptent le plus pour les utilisateurs |
| Temps de réponse | selon l'usage | ce que les utilisateurs acceptent : quelques secondes au bureau, moins sur le terrain |
| Coût par question | selon l'usage | ce que le projet peut payer, multiplié par le nombre de questions posées chaque jour |

Ces repères viennent de la méthode, [Évaluer le RAG avec le corpus](methode_et_contrat/methode_evaluation.md). On les ajuste avec le métier, avant de lui présenter les scores : par exemple 95 % de réponses justes pour une application de sécurité, ou un temps de réponse plus long pour une recherche documentaire rare.

## 2. Lire l'intervalle de confiance

Chaque pourcentage du rapport est donné avec une fourchette, par exemple « 69 % (entre 44 et 94 %) ». C'est l'intervalle de confiance : le vrai résultat du RAG, celui qu'on mesurerait avec beaucoup plus de questions, a 95 chances sur 100 de s'y trouver.

- **Une fourchette large veut dire que le score est imprécis**, parce qu'il est calculé sur peu de questions. « 69 % (entre 44 et 94 %) » est compté sur 13 questions : le RAG peut être médiocre comme très bon.
- **Si la fourchette contient le repère, on ne peut pas conclure.** Le score peut être au-dessus comme en dessous. Il faut plus de questions, ou lire les questions ratées une par une.
- **Combien de questions pour un score précis** : pour une fourchette d'environ ± 10 points, il faut de 60 à 100 questions ; pour ± 5 points, de 250 à 400.
- Un score de 0 % ou de 100 % n'a pas de fourchette dans le rapport. Cela ne veut pas dire qu'il est certain : sur peu de questions, il reste imprécis.

## 3. Comparer deux configurations, ou deux RAG

Pour choisir une configuration, garder une amélioration, ou comparer deux RAG sur le même corpus :

- **un écart plus petit que la fourchette ne prouve rien seul** : il peut venir du hasard ;
- on regarde alors **les questions gagnées et perdues**, une par une ;
- **une question grave perdue est un recul**, même si la moyenne monte ;
- le rapport de comparaison fait ces trois vérifications : [5. Résultats et comparaison](5_resultats_et_comparaison.md#5-comparer-deux-versions).

## 4. Présenter les scores à ceux qui décident

Dans cet ordre :

1. **L'état du juge**, en tête du rapport : s'il n'est pas validé, le score « Réponses justes » est incertain.
2. **Les fuites de droits et les erreurs graves**, avec chaque question concernée : elles pèsent plus que tout le reste.
3. **Les scores clés**, chacun avec sa phrase et sa fourchette, à côté de son repère.
4. **Les questions ratées** qui comptent le plus pour les utilisateurs : celles qui sont fréquentes ou graves.
5. **Ce qu'il faudrait corriger**, et ce que ça changerait : le rapport dit si chaque échec vient de la lecture des documents, de la recherche ou de la réponse.

C'est ensuite à eux de décider si c'est satisfaisant.

Retour au [fil conducteur](../FIL_CONDUCTEUR.md#4-lire-le-rapport-comparer-faire-décider-le-métier), étape 4.
