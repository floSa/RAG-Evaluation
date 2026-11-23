# Évaluation de la configuration `graphrag-hybride-k5-57001489`

Ce rapport donne les scores d'**une configuration** du RAG sur le corpus du métier. Il ne décide pas : c'est au métier de dire, à leur lecture, si cette configuration peut partir en production.

Corpus : version 2026-11-20.1, 60 questions, dont 20 réservées aux scores clés. Juge : chat, prompt 1.0.

## La configuration évaluée

Les réglages du RAG pendant cette évaluation, tels qu'il les a déclarés.

| Réglage | Valeur |
| --- | --- |
| Type de recherche | hybride |
| Morceaux de texte ramenés par question (k) | 5 |
| Découpage des documents | sections-1 |
| Modèle qui vectorise le texte | embed |
| Modèle qui écrit la réponse | gemma-4-e4b |
| Version du prompt | 1.0 |
| Reclassement des morceaux (reranker) | aucun |

## 1. Les scores clés

Ce sont les scores à présenter au métier. Ils sont calculés sur les 20 questions réservées, jamais utilisées pour régler le RAG ; les fuites de droits et les erreurs graves, sur toutes les questions. Entre parenthèses, la fourchette où se trouve le vrai résultat : avec peu de questions, elle est large.

| Ce qui est mesuré | Résultat | Ce que ça veut dire |
| --- | --- | --- |
| Documents présents dans la base | 100 % | 50 documents sur 50 sont dans la base du RAG. |
| Étiquettes complètes | 100 % | 1059 morceaux de texte sur 1059 indiquent leur source, leur page et leurs droits d'accès. |
| Passages du métier retrouvés | 100 % | 30 passages du métier sur 30 se retrouvent dans un morceau de la base. |
| Erreur de lecture des scans (caractères) | 15 % | Sur les pages scannées, 15 caractères sur 100 sont mal lus. |
| Bon passage ramené | 69 % (entre 44 et 94 %) | Pour 9 questions sur 13, la recherche ramène le passage qui contient la réponse. |
| Fuites de droits | 0 | Questions qui ont ramené un document interdit à la personne qui la pose : 0. |
| Réponses justes | 88 % (entre 69 et 100 %) | Sur 12 questions, l'équivalent de 10 réponses justes (une réponse partielle compte pour moitié). |
| Sait dire « je ne sais pas » | 100 % | Sur 5 questions sans réponse dans les documents ou interdites à la personne, le RAG dit « je ne sais pas » 5 fois. |
| Fidélité aux documents | 97 % (entre 88 et 100 %) | 97 affirmations sur 100 des réponses se trouvent dans les documents ramenés. |
| Erreurs graves | 0 | Réponses fausses, inventées ou données à tort, sur une question où l'erreur a des conséquences graves : 0. |
| Score pondéré | 78 % (entre 60 et 96 %) | 78 réponses justes sur 100, en comptant davantage les questions fréquentes et graves. |
| Temps de réponse médian | 7,9 s | La moitié des réponses arrivent en moins de 7,9 s. |
| Temps de réponse à 95 % | 12,8 s | 95 réponses sur 100 arrivent en moins de 12,8 s. |
| Coût par question | 0,00 € | Une réponse coûte en moyenne 0,00 €. |

## 2. Tous les scores, évaluation par évaluation

Sur les 40 autres questions, celles qui servent à régler le RAG. On les lit dans l'ordre : une réponse fausse vient souvent d'un passage perdu à l'ingestion ou mal retrouvé par la recherche. Un score compté sur moins de 10 cas est une tendance, pas une mesure. Le calcul de chaque score est détaillé dans les guides 1 à 4 du service d'évaluation ; le code sert à le retrouver dans les fichiers techniques.

### 1. Ingestion

On vérifie que le RAG n'a rien perdu ni abîmé en lisant les documents, en les découpant en morceaux de texte et en les rangeant dans sa base.

| Score | Résultat | Ce que ça veut dire | Code |
| --- | --- | --- | --- |
| Documents présents dans la base | 100 % | 50 documents sur 50 sont dans la base du RAG. | `n1_documents_indexes` |
| Étiquettes complètes | 100 % | 1059 morceaux de texte sur 1059 indiquent leur source, leur page et leurs droits d'accès. | `n1_metadonnees_completes` |
| Passages du métier retrouvés | 100 % | 61 passages du métier sur 61 se retrouvent dans un morceau de la base. | `n1_passages_rattaches` |
| Passages coupés en deux | 0 % | 0 passages du métier sur 61 sont coupés entre deux morceaux. | `n1_passages_coupes` |
| Erreur de lecture des scans (caractères) | 15 % | Sur les pages scannées, 15 caractères sur 100 sont mal lus. | `n1_erreur_caracteres` |
| Erreur de lecture des scans (mots) | 20 % | Sur les pages scannées, 20 mots sur 100 sont mal lus. | `n1_erreur_mots` |
| Violations des règles du graphe | 25 | Relations du graphe qui ne respectent pas les règles de l'ontologie : 25. | `n1_graphe_violations` |

### 2. Recherche

On vérifie que, pour chaque question, la recherche ramène les morceaux qui contiennent la réponse, et jamais un morceau d'un document interdit à la personne qui pose la question.

| Score | Résultat | Ce que ça veut dire | Code |
| --- | --- | --- | --- |
| Bon passage ramené | 82 % (entre 68 et 96 %) | Pour 23 questions sur 28, la recherche ramène le passage qui contient la réponse. | `n2_reussite_k` |
| Passages nécessaires ramenés | 81 % (entre 69 et 93 %) | 34 passages nécessaires sur 42 sont ramenés par la recherche. | `n2_rappel_k` |
| Bon morceau en tête | 59 % (entre 40 et 77 %) | 59 sur 100 : 100 si le bon morceau arrive toujours 1er, 50 s'il arrive en moyenne 2e. | `n2_rang_premier` |
| Fuites de droits | 0 | Questions qui ont ramené un document interdit à la personne qui la pose : 0. | `n2_fuite_droits` |
| Bon passage ramené, si k = 1 | 39 % (entre 21 et 57 %) | Pour 11 questions sur 28, le bon passage serait ramené avec 1 seul morceau. | `n2_reussite_1` |
| Bon passage ramené, si k = 3 | 71 % (entre 55 et 88 %) | Pour 20 questions sur 28, le bon passage serait ramené avec 3 morceaux. | `n2_reussite_3` |
| Bon passage ramené, si k = 5 | 82 % (entre 68 et 96 %) | Pour 23 questions sur 28, le bon passage serait ramené avec 5 morceaux. | `n2_reussite_5` |
| Pièges ou version périmée devant le bon | 4 % (entre 0 et 10 %) | Pour 1 questions sur 28, un piège ou une ancienne version passe devant le bon passage. | `n2_perimes_pieges` |

### 3. Réponse

On vérifie que la réponse écrite par le RAG est juste, qu'elle ne dit que ce que disent les documents, et que le RAG sait dire « je ne sais pas ».

| Score | Résultat | Ce que ça veut dire | Code |
| --- | --- | --- | --- |
| Réponses justes | 90 % (entre 78 et 100 %) | Sur 25 questions, l'équivalent de 22 réponses justes (une réponse partielle compte pour moitié). | `n3_exactitude` |
| Listes complètes | 100 % | Quand la réponse est une liste, elle donne 100 éléments attendus sur 100. | `n3_completude_listes` |
| Chiffres exacts | 91 % (entre 76 et 100 %) | 91 chiffres attendus sur 100 sont dans la réponse, avec la bonne unité. | `n3_valeurs` |
| Sait dire « je ne sais pas » | 100 % | Sur 8 questions sans réponse dans les documents ou interdites à la personne, le RAG dit « je ne sais pas » 8 fois. | `n3_abstention_correcte` |
| Abstentions à tort | 9 % (entre 0 et 19 %) | Pour 3 questions sur 32, le RAG dit « je ne sais pas » alors que la réponse était dans ce qu'il a ramené. | `n3_abstention_a_tort` |
| Fidélité aux documents | 95 % (entre 86 et 100 %) | 95 affirmations sur 100 des réponses se trouvent dans les documents ramenés. | `n3_fidelite` |
| Bonnes sources citées | 100 % | Pour 25 questions sur 25, la réponse cite le passage qui contient la réponse. | `n3_citations` |
| Erreurs graves | 0 | Réponses fausses, inventées ou données à tort, sur une question où l'erreur a des conséquences graves : 0. | `n3_erreurs_graves` |
| Synthèses | 73 % | Le juge note les synthèses sur une grille : 73 sur 100. | `n3_synthese` |
| Questions de suite justes | 100 % | Sur 3 questions de suite, l'équivalent de 3 réponses justes. | `n3_questions_suite` |
| Reformulations incohérentes | 0 % | 0 groupes de questions reformulées sur 6 reçoivent des réponses différentes. | `n3_variantes` |

### 4. Bout en bout

On vérifie que le RAG est bon sur les questions qui comptent le plus, assez rapide et pas trop cher.

| Score | Résultat | Ce que ça veut dire | Code |
| --- | --- | --- | --- |
| Score pondéré | 82 % (entre 70 et 94 %) | 82 réponses justes sur 100, en comptant davantage les questions fréquentes et graves. | `n4_score_pondere` |
| Erreurs graves | 0 | Les mêmes erreurs graves que dans l'évaluation de la réponse : 0. | `n4_erreurs_graves` |
| Temps de réponse médian | 7,4 s | La moitié des réponses arrivent en moins de 7,4 s. | `n4_temps_median` |
| Temps de réponse à 95 % | 10,7 s | 95 réponses sur 100 arrivent en moins de 10,7 s. | `n4_temps_p95` |
| Coût par question | 0,00 € | Une réponse coûte en moyenne 0,00 €. | `n4_cout_moyen` |

## 3. Les questions à regarder en premier

Erreurs graves et fuites d'abord, puis réponses fausses, puis passages perdus à l'ingestion. Le détail de chaque question est dans `resultats_par_question.csv`.

| Question | Problème | Détail |
| --- | --- | --- |
| **Q-041** : quels problèmes électriques reviennent le plus souvent dans les interventions des deux usines ? | Réponse fausse | 1. contredit : La réponse de référence mentionne des 'échauffements', tandis que l'assistant parle de 'desserrage'. Bien que liés, ce n'est pas la même expression technique et cela peut être considéré comme une contradiction s'il faut exprimer exactement le même sens. ; 2. absent : L'information concernant les 'défauts d'isolement sur le site B' n'est pas mentionnée dans la réponse de l'assistant. |

## 4. La faute est-elle dans la recherche ou dans la réponse ?

Pour chaque question qui a une réponse dans les documents : le bon passage a-t-il été ramené, et la réponse est-elle juste ?

| Diagnostic | Questions | Que corriger |
| --- | --- | --- |
| tout va bien | 21 | — |
| génération : le bon morceau était retrouvé | 4 | le prompt ou le modèle de génération |
| recherche : le bon morceau n'est pas retrouvé | 4 | la lecture des documents, le découpage ou la recherche |
| génération : le bon morceau était retrouvé (abstention à tort) | 3 | le prompt ou le modèle de génération |

## 5. Par type de document

| Score | Compte rendu d'intervention | Note technique | Procédure | questions sans passage |
| --- | --- | --- | --- | --- |
| Passages du métier retrouvés | 100 % (n = 10) | 100 % (n = 27) | 100 % (n = 24) | — |
| Bon passage ramené | 25 % (n = 4) | 88 % (n = 16) | 100 % (n = 14) | — |
| Réponses justes | 50 % (n = 2) | 85 % (n = 17) | 97 % (n = 16) | — |
| Fidélité aux documents | 100 % (n = 2) | 95 % (n = 17) | 92 % (n = 16) | — |
| Score pondéré | 18 % (n = 6) | 80 % (n = 20) | 91 % (n = 17) | 100 % (n = 7) |

## Les fichiers techniques de cette évaluation

Ils sont dans `fichiers_techniques/`. Ce rapport en est tiré ; on ne les ouvre que pour creuser.

| Fichier | Contenu |
| --- | --- |
| `rapport.html` | ce rapport, en page web |
| `scores.json` | tous les scores, avec leur marge d'erreur et leur détail par type de document, de question… |
| `resultats_par_question.csv` | une ligne par question et par score, avec la justification du juge : à ouvrir dans un tableur |
| `croisement.jsonl` | pour chaque question : bon passage ramené ou non, réponse juste ou non |
| `liens_index.jsonl` | chaque passage du métier et le morceau de la base où il a été retrouvé |
| `passages_non_rattaches.jsonl` | les passages du métier introuvables dans la base, avec leur cause probable |
| `relecture.jsonl` | les réponses que le métier doit relire, et pourquoi |
| `evaluation.json` | ce qui a été évalué : versions du corpus, du service, du RAG et du juge |
