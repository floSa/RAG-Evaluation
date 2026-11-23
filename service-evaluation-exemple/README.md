# Service d'évaluation, exemple

Ce dossier montre le [service d'évaluation](../service-evaluation/README.md) **une fois qu'il a tourné** sur le [RAG d'exemple](../service-rag-exemple/README.md). Il a exactement les mêmes dossiers que `service-evaluation/`, mais remplis : la configuration, le corpus annoté, et tous les résultats. Tout se lit ici, sans rien installer.

## Ce qui a été évalué

**Le corpus** : 50 documents fictifs sur la maintenance électrique d'une entreprise inventée (procédures, notes techniques dont 5 scannées, comptes rendus d'intervention), et 60 questions écrites par le métier, avec leur bonne réponse et l'endroit des documents où elle se trouve. 40 questions servent à régler le RAG. Les 20 autres sont **réservées à la décision** : on ne les regarde jamais pendant les réglages, pour ne pas régler le RAG « pour l'examen ».

**Le RAG** : le RAG d'exemple, dans quatre configurations. Une configuration, c'est le RAG avec tous ses réglages fixés. La configuration de **référence** est celle de départ :

| Réglage | Valeur dans la référence | Ce que c'est |
| --- | --- | --- |
| Type de recherche | vectorielle | le RAG compare le sens de la question à celui de chaque morceau de texte, grâce à des vecteurs |
| Nombre de morceaux ramenés (k) | 5 | pour chaque question, la recherche ramène 5 morceaux, que le modèle lit pour écrire sa réponse |
| Découpage | par section | chaque document est coupé en morceaux qui suivent ses titres |
| Modèle de génération | gemma-4-e4b, avec réflexion | le modèle qui écrit la réponse ; « avec réflexion » : il raisonne avant de répondre |
| Graphe | aucun | pas de carte des liens entre équipements, sites et personnes |

Les trois autres configurations changent **un seul réglage** chacune, pour mesurer son effet :

| Configuration | Le réglage changé |
| --- | --- |
| k = 3 | la recherche ramène 3 morceaux au lieu de 5 |
| Sans réflexion | le modèle écrit sa réponse directement, sans raisonner d'abord |
| Hybride | un graphe est ajouté : le RAG consulte aussi les liens entre équipements, sites et personnes, extraits des documents |

## Sur quoi se fonde la décision

Avant d'évaluer, le métier a fixé des **seuils** dans [`config/seuils.json`](config/seuils.json). Par exemple : au moins 95 % des passages du métier retrouvés dans la base du RAG, au moins 90 % de questions où la recherche ramène le bon passage, au moins 80 % de réponses justes, une réponse en moins de 15 secondes.

Une configuration peut partir en production si **tous les seuils sont atteints sur les 20 questions réservées**, et si elle ne fait **aucune erreur grave ni aucune fuite de droits**, sur l'ensemble des questions. Une erreur grave, c'est une réponse fausse ou inventée à une question que le métier a jugée grave. Une fuite de droits, c'est montrer un document réservé à quelqu'un qui n'y a pas droit.

## 1. Les quatre configurations évaluées

| Configuration | Réponses justes | Score pondéré | Décision | Pourquoi | Rapport |
| --- | --- | --- | --- | --- | --- |
| **Référence** | 79 % | 80 % | ❌ non recommandée | 1 erreur grave ; seuils manqués : lecture des scans, bon passage ramené, réponses justes, score pondéré | [lire](resultats/evaluations/2026-11-20.1_graphrag-vectoriel-k5-5954e822/RAPPORT.md) |
| k = 3 | 83 % | 77 % | ❌ non recommandée | seuils manqués : lecture des scans, bon passage ramené, score pondéré | [lire](resultats/evaluations/2026-11-20.1_graphrag-vectoriel-k3-5954e822/RAPPORT.md) |
| Sans réflexion | 71 % | 77 % | ❌ non recommandée | seuils manqués : lecture des scans, bon passage ramené, réponses justes, score pondéré | [lire](resultats/evaluations/2026-11-20.1_graphrag-vectoriel-k5-94d362c8/RAPPORT.md) |
| Hybride | 90 % | 82 % | ❌ non recommandée | seuils manqués : lecture des scans, bon passage ramené, score pondéré | [lire](resultats/evaluations/2026-11-20.1_graphrag-hybride-k5-57001489/RAPPORT.md) |

Les deux colonnes de chiffres portent sur les 40 questions de réglage ; la décision, elle, se juge sur les 20 questions réservées.

- **Réponses justes** : un modèle juge compare chaque réponse à la bonne réponse du métier. Une réponse juste compte 1, une réponse partielle 0,5, une réponse fausse 0.
- **Score pondéré** : la même note, mais chaque question compte selon sa fréquence et sa gravité, fixées par le métier. C'est le chiffre le plus proche de ce que vivront les utilisateurs.

**Aucune configuration n'est prête.** Les quatre butent sur les mêmes points :
- les pages scannées sont mal lues : 15 % de caractères faux, pour un seuil de 2 % ;
- la recherche ne ramène pas assez souvent le bon passage.

## 2. Les trois comparaisons avec la référence

| Comparaison | Ce qu'on en conclut | Rapport |
| --- | --- | --- |
| Référence contre **k = 3** | **Pas meilleure.** Avec 3 morceaux, la recherche ramène moins souvent le bon passage (75 % contre 86 %) : 4 questions perdues, aucune gagnée. Elle n'a plus d'erreur grave, mais seulement parce qu'elle ne répond pas à la question en cause (Q-046). | [lire](resultats/comparaisons_de_configurations/2026-11-20.1_graphrag-vectoriel-k5-5954e822_contre_graphrag-vectoriel-k3-5954e822/RAPPORT.md) |
| Référence contre **sans réflexion** | **On garde la réflexion.** Sans elle, le RAG répond 9 fois plus vite (0,9 s contre 7,4 s), mais calcule mal : 75 % de chiffres exacts contre 91 %. Avec la réflexion, 7,4 s reste sous le seuil de 15 s. | [lire](resultats/comparaisons_de_configurations/2026-11-20.1_graphrag-vectoriel-k5-5954e822_contre_graphrag-vectoriel-k5-94d362c8/RAPPORT.md) |
| Référence contre **hybride** | **Rien de mesurable.** Le graphe fait gagner 2 questions et en perdre 1 : l'écart peut venir du hasard. Ce corpus a peu de questions qui demandent de suivre des liens entre documents. | [lire](resultats/comparaisons_de_configurations/2026-11-20.1_graphrag-vectoriel-k5-5954e822_contre_graphrag-hybride-k5-57001489/RAPPORT.md) |

## Ce qu'il y a dans ce dossier

Les mêmes dossiers que dans `service-evaluation/`, remplis :

| Dossier | Ce qu'il contient ici |
| --- | --- |
| [`config/`](config/) | nos réglages, et les seuils fixés par le métier |
| [`corpus_annote/`](corpus_annote/) | le corpus documentaire (50 documents) et le fichier Excel du métier rempli ; plus, pour ce banc d'essai seulement, les notes du métier simulées et le script qui a fabriqué les documents |
| [`resultats/`](resultats/) | le corpus contrôlé, les réponses du RAG pour chaque configuration, les 4 évaluations et les 3 comparaisons |

Chaque évaluation et chaque comparaison est un dossier nommé d'après la version du RAG évaluée. Exemple : `2026-11-20.1_graphrag-vectoriel-k5-5954e822` = le corpus du 20 novembre, le RAG « graphrag » en recherche vectorielle, avec k = 5, et une empreinte de ses autres réglages. Le tableau de la partie 1 dit à quelle configuration chacun correspond.
