# Évaluation de la configuration `graphrag-vectoriel-k5-5954e822`

Ce rapport donne les scores d'**une configuration** du RAG sur le corpus du métier. Il ne décide pas : c'est au métier de dire, à leur lecture, si cette configuration peut partir en production.

|  |  |
| --- | --- |
| Configuration évaluée | RAG vectoriel, k = 5, découpage sections-1, embeddings embed, génération gemma-4-e4b, prompt 1.0, reranker aucun |
| Corpus | version 2026-11-20.1 : 60 questions, dont 20 réservées aux scores clés |
| Juge | chat, prompt 1.0 |

## 1. Les scores clés

Ce sont les scores à présenter au métier. Ils sont calculés sur les 20 questions réservées, jamais utilisées pour régler le RAG ; les fuites de droits et les erreurs graves, sur toutes les questions. Entre parenthèses, la fourchette où se trouve le vrai résultat : avec peu de questions, elle est large.

| Ce qui est mesuré | Résultat | Ce que ça veut dire |
| --- | --- | --- |
| Documents présents dans la base | 100 % | 50 documents sur 50 sont dans la base du RAG. |
| Étiquettes complètes | 100 % | 534 morceaux de texte sur 534 indiquent leur source, leur page et leurs droits d'accès. |
| Passages du métier retrouvés | 100 % | 30 passages du métier sur 30 se retrouvent dans un morceau de la base. |
| Erreur de lecture des scans (caractères) | 15 % | Sur les pages scannées, 15 caractères sur 100 sont mal lus. |
| Bon passage ramené | 69 % (entre 44 et 94 %) | Pour 9 questions sur 13, la recherche ramène le passage qui contient la réponse. |
| Fuites de droits | 0 | Questions qui ont ramené un document interdit à la personne qui la pose : 0. |
| Réponses justes | 77 % (entre 54 et 100 %) | Sur 13 questions, l'équivalent de 10 réponses justes (une réponse partielle compte pour moitié). |
| Sait dire « je ne sais pas » | 100 % | Sur 5 questions sans réponse dans les documents ou interdites à la personne, le RAG dit « je ne sais pas » 5 fois. |
| Fidélité aux documents | 98 % (entre 91 et 100 %) | 98 affirmations sur 100 des réponses se trouvent dans les documents ramenés. |
| Erreurs graves | 1 | Réponses fausses, inventées ou données à tort, sur une question où l'erreur a des conséquences graves : 1. |
| Score pondéré | 76 % (entre 57 et 95 %) | 76 réponses justes sur 100, en comptant davantage les questions fréquentes et graves. |
| Temps de réponse médian | 8,0 s | La moitié des réponses arrivent en moins de 8,0 s. |
| Temps de réponse à 95 % | 14,7 s | 95 réponses sur 100 arrivent en moins de 14,7 s. |
| Coût par question | 0,00 € | Une réponse coûte en moyenne 0,00 €. |

## 2. Tous les scores, évaluation par évaluation

Sur les 40 autres questions, celles qui servent à régler le RAG. On les lit dans l'ordre : une réponse fausse vient souvent d'un passage perdu à l'ingestion ou mal retrouvé par la recherche. Un score compté sur moins de 10 cas est une tendance, pas une mesure. Le calcul de chaque score est détaillé dans les guides 1 à 4 du service d'évaluation ; le code sert à le retrouver dans les fichiers techniques.

### 1. Ingestion

On vérifie que le RAG n'a rien perdu ni abîmé en lisant les documents, en les découpant en morceaux de texte et en les rangeant dans sa base.

| Score | Résultat | Ce que ça veut dire | Code |
| --- | --- | --- | --- |
| Documents présents dans la base | 100 % | 50 documents sur 50 sont dans la base du RAG. | `n1_documents_indexes` |
| Étiquettes complètes | 100 % | 534 morceaux de texte sur 534 indiquent leur source, leur page et leurs droits d'accès. | `n1_metadonnees_completes` |
| Passages du métier retrouvés | 100 % | 61 passages du métier sur 61 se retrouvent dans un morceau de la base. | `n1_passages_rattaches` |
| Passages coupés en deux | 0 % | 0 passages du métier sur 61 sont coupés entre deux morceaux. | `n1_passages_coupes` |
| Erreur de lecture des scans (caractères) | 15 % | Sur les pages scannées, 15 caractères sur 100 sont mal lus. | `n1_erreur_caracteres` |
| Erreur de lecture des scans (mots) | 20 % | Sur les pages scannées, 20 mots sur 100 sont mal lus. | `n1_erreur_mots` |

### 2. Recherche

On vérifie que, pour chaque question, la recherche ramène les morceaux qui contiennent la réponse, et jamais un morceau d'un document interdit à la personne qui pose la question.

| Score | Résultat | Ce que ça veut dire | Code |
| --- | --- | --- | --- |
| Bon passage ramené | 86 % (entre 73 et 99 %) | Pour 24 questions sur 28, la recherche ramène le passage qui contient la réponse. | `n2_reussite_k` |
| Passages nécessaires ramenés | 81 % (entre 69 et 93 %) | 34 passages nécessaires sur 42 sont ramenés par la recherche. | `n2_rappel_k` |
| Bon morceau en tête | 68 % (entre 51 et 86 %) | 68 sur 100 : 100 si le bon morceau arrive toujours 1er, 50 s'il arrive en moyenne 2e. | `n2_rang_premier` |
| Fuites de droits | 0 | Questions qui ont ramené un document interdit à la personne qui la pose : 0. | `n2_fuite_droits` |
| Bon passage ramené, si k = 1 | 54 % (entre 35 et 72 %) | Pour 15 questions sur 28, le bon passage serait ramené avec 1 seul morceau. | `n2_reussite_1` |
| Bon passage ramené, si k = 3 | 75 % (entre 59 et 91 %) | Pour 21 questions sur 28, le bon passage serait ramené avec 3 morceaux. | `n2_reussite_3` |
| Bon passage ramené, si k = 5 | 86 % (entre 73 et 99 %) | Pour 24 questions sur 28, le bon passage serait ramené avec 5 morceaux. | `n2_reussite_5` |
| Pièges ou version périmée devant le bon | 0 % | Pour 0 questions sur 28, un piège ou une ancienne version passe devant le bon passage. | `n2_perimes_pieges` |

### 3. Réponse

On vérifie que la réponse écrite par le RAG est juste, qu'elle ne dit que ce que disent les documents, et que le RAG sait dire « je ne sais pas ».

| Score | Résultat | Ce que ça veut dire | Code |
| --- | --- | --- | --- |
| Réponses justes | 79 % (entre 63 et 94 %) | Sur 28 questions, l'équivalent de 22 réponses justes (une réponse partielle compte pour moitié). | `n3_exactitude` |
| Listes complètes | 100 % | Quand la réponse est une liste, elle donne 100 éléments attendus sur 100. | `n3_completude_listes` |
| Chiffres exacts | 91 % (entre 76 et 100 %) | 91 chiffres attendus sur 100 sont dans la réponse, avec la bonne unité. | `n3_valeurs` |
| Sait dire « je ne sais pas » | 100 % | Sur 8 questions sans réponse dans les documents ou interdites à la personne, le RAG dit « je ne sais pas » 8 fois. | `n3_abstention_correcte` |
| Abstentions à tort | 6 % (entre 0 et 15 %) | Pour 2 questions sur 32, le RAG dit « je ne sais pas » alors que la réponse était dans ce qu'il a ramené. | `n3_abstention_a_tort` |
| Fidélité aux documents | 95 % (entre 87 et 100 %) | 95 affirmations sur 100 des réponses se trouvent dans les documents ramenés. | `n3_fidelite` |
| Bonnes sources citées | 93 % (entre 83 et 100 %) | Pour 26 questions sur 28, la réponse cite le passage qui contient la réponse. | `n3_citations` |
| Erreurs graves | 1 | Réponses fausses, inventées ou données à tort, sur une question où l'erreur a des conséquences graves : 1. | `n3_erreurs_graves` |
| Synthèses | 65 % | Le juge note les synthèses sur une grille : 65 sur 100. | `n3_synthese` |
| Questions de suite justes | 100 % | Sur 3 questions de suite, l'équivalent de 3 réponses justes. | `n3_questions_suite` |
| Reformulations incohérentes | 0 % | 0 groupes de questions reformulées sur 6 reçoivent des réponses différentes. | `n3_variantes` |

### 4. Bout en bout

On vérifie que le RAG est bon sur les questions qui comptent le plus, assez rapide et pas trop cher.

| Score | Résultat | Ce que ça veut dire | Code |
| --- | --- | --- | --- |
| Score pondéré | 80 % (entre 68 et 93 %) | 80 réponses justes sur 100, en comptant davantage les questions fréquentes et graves. | `n4_score_pondere` |
| Erreurs graves | 1 | Les mêmes erreurs graves que dans l'évaluation de la réponse : 1. | `n4_erreurs_graves` |
| Temps de réponse médian | 7,4 s | La moitié des réponses arrivent en moins de 7,4 s. | `n4_temps_median` |
| Temps de réponse à 95 % | 12,8 s | 95 réponses sur 100 arrivent en moins de 12,8 s. | `n4_temps_p95` |
| Coût par question | 0,00 € | Une réponse coûte en moyenne 0,00 €. | `n4_cout_moyen` |

## 3. Les questions à regarder en premier

Erreurs graves et fuites d'abord, puis réponses fausses, puis passages perdus à l'ingestion. Le détail de chaque question est dans `resultats_par_question.csv`.

| Question | Problème | Détail |
| --- | --- | --- |
| **Q-046** : quelles règles de sécurité retrouve-t-on dans toutes les interventions électriques ? | Erreur grave | 1. absent : L'assistant ne mentionne pas l'habilitation adaptée et à jour. ; 2. absent : L'assistant ne mentionne pas la consignation avant travaux. ; 3. absent : L'assistant ne mentionne pas la vérification d'absence de tension. ; 4. absent : L'assistant ne mentionne pas l'interdiction de travailler seul en HTA. ; 5. absent : L'assistant ne mentionne pas l'attente de la décharge des condensateurs |
| **Q-030** : quelles interventions a-t-on faites sur l'armoire AD-A07, et qu'est-ce qui a été fait à chaque fois ? | Réponse fausse | 1. absent : L'assistant mentionne le problème de déclenchement mais ne décrit pas l'intervention effectuée (séparation en deux circuits) ni la date précise (avril 2025). ; 2. contredit : L'assistant indique que la suite donnée à l'intervention OT-24112 était 'Aucune', alors que la référence précise qu'il y a eu un remplacement du différentiel. |
| **Q-041** : quels problèmes électriques reviennent le plus souvent dans les interventions des deux usines ? | Réponse fausse | 1. absent : L'assistant mentionne le desserrage des connexions (cause racine) mais ne cite pas explicitement l'échauffement de connexions comme problème électrique récurrent tel que défini dans les points clés. ; 2. absent : L'information concernant les défauts d'isolement sur le site B n'est pas mentionnée. ; 3. absent : L'information concernant les déclenchements intempestifs de différentiels n' |
| **Q-043** : quels enseignements tirer des campagnes de thermographie depuis 2023 ? | Réponse fausse | 1. present : L'assistant identifie le desserrage des connexions comme la première cause d'échauffement. ; 2. present : Les points chauds récurrents sur les arrivées du TGBT-A et l'armoire AD-B04 sont mentionnés. ; 3. contredit : L'assistant indique que la périodicité est passée de 24 à 12 mois 'à partir de 2025', alors que la référence précise que le changement s'est produit depuis 2023. ; 4. pres |

## 4. La faute est-elle dans la recherche ou dans la réponse ?

Pour chaque question qui a une réponse dans les documents : le bon passage a-t-il été ramené, et la réponse est-elle juste ?

| Diagnostic | Questions | Que corriger |
| --- | --- | --- |
| tout va bien | 20 | — |
| génération : le bon morceau était retrouvé | 6 | le prompt ou le modèle de génération |
| recherche : le bon morceau n'est pas retrouvé | 4 | la lecture des documents, le découpage ou la recherche |
| génération : le bon morceau était retrouvé (abstention à tort) | 2 | le prompt ou le modèle de génération |

## 5. Par type de document

| Score | Compte rendu d'intervention | Note technique | Procédure | questions sans passage |
| --- | --- | --- | --- | --- |
| Passages du métier retrouvés | 100 % (n = 10) | 100 % (n = 27) | 100 % (n = 24) | — |
| Bon passage ramené | 50 % (n = 4) | 88 % (n = 16) | 100 % (n = 14) | — |
| Réponses justes | 25 % (n = 4) | 76 % (n = 17) | 85 % (n = 17) | — |
| Fidélité aux documents | 100 % (n = 4) | 95 % (n = 17) | 95 % (n = 17) | — |
| Score pondéré | 9 % (n = 6) | 74 % (n = 20) | 89 % (n = 17) | 100 % (n = 7) |

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
