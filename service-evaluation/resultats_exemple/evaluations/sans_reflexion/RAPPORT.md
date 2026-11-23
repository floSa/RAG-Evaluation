# Évaluation de la configuration `graphrag-vectoriel-k5-94d362c8`

Ce rapport évalue **une configuration** du RAG sur le corpus du métier. Il répond à une question : **cette configuration peut-elle partir en production ?**

|  |  |
| --- | --- |
| Configuration évaluée | RAG vectoriel, k = 5, découpage sections-1, embeddings embed, génération gemma-4-e4b, prompt 1.0, reranker aucun |
| Corpus | version 2026-11-20.1 : 60 questions, dont 20 réservées à la décision |
| Juge | chat, prompt 1.0 |

## 1. La décision

**❌ Mise en production non recommandée.**

- Seuil(s) non atteint(s) : Erreur de lecture des scans (caractères), Bon passage ramené, Réponses justes, Score pondéré.

Les seuils sont fixés par le métier avant l'évaluation. Ils se jugent sur les 20 questions réservées à la décision, jamais utilisées pour régler le RAG. Les critères bloquants (fuite de droits, erreur grave) se jugent sur toutes les questions.

| Ce qui est vérifié | Résultat | Seuil | Atteint ? | Compté sur |
| --- | --- | --- | --- | --- |
| Documents présents dans la base | 100 % | ≥ 100 % | ✅ oui | 50 |
| Étiquettes complètes | 100 % | ≥ 100 % | ✅ oui | 534 |
| Passages du métier retrouvés | 100 % | ≥ 95 % | ✅ oui | 30 |
| Erreur de lecture des scans (caractères) | 15 % | ≤ 2 % | ❌ non | 20 |
| Bon passage ramené | 69 % ± 25 | ≥ 90 % | ❌ non | 13 |
| Fuites de droits | 0 | ≤ 0 | ✅ oui | 60 |
| Réponses justes | 61 % ± 26 | ≥ 80 % | ❌ non | 14 |
| Sait dire « je ne sais pas » | 100 % | ≥ 80 % | ✅ oui | 5 |
| Fidélité aux documents | 95 % ± 12 | ≥ 90 % | ✅ oui | 14 |
| Erreurs graves | 0 | ≤ 0 | ✅ oui | 12 |
| Score pondéré | 73 % ± 20 | ≥ 80 % | ❌ non | 20 |
| Temps de réponse médian | 0,8 s | ≤ 15,0 s | ✅ oui | 20 |
| Temps de réponse à 95 % | 4,5 s | ≤ 30,0 s | ✅ oui | 20 |
| Coût par question | 0,00 € | ≤ 0,05 € | ✅ oui | 20 |

## 2. Les scores, évaluation par évaluation

Sur les 40 questions de réglage. On les lit dans l'ordre : une réponse fausse vient souvent d'un passage perdu à l'ingestion ou mal retrouvé par la recherche. « ± » est la marge d'erreur : un écart plus petit ne veut rien dire. Un score compté sur moins de 10 éléments est une tendance, pas une mesure. Comment chaque score est calculé : les guides 1 à 4 du service d'évaluation.

### 1. Ingestion

On vérifie que le service d'ingestion n'a rien perdu ni abîmé en découpant les documents, en les vectorisant et en les rangeant dans la base vectorielle.

| Score | Ce qu'il compte | Résultat | Seuil | Atteint ? | Compté sur | Code |
| --- | --- | --- | --- | --- | --- | --- |
| Documents présents dans la base | documents qui ont au moins un morceau dans la base ÷ documents envoyés | 100 % | ≥ 100 % | ✅ oui | 50 | `n1_documents_indexes` |
| Étiquettes complètes | morceaux qui indiquent leur document, leur page et leurs droits d'accès ÷ morceaux | 100 % | ≥ 100 % | ✅ oui | 534 | `n1_metadonnees_completes` |
| Passages du métier retrouvés | passages du métier retrouvés dans un morceau de la base ÷ passages du métier | 100 % | ≥ 95 % | ✅ oui | 61 | `n1_passages_rattaches` |
| Passages coupés en deux | passages retrouvés seulement à cheval sur deux morceaux ÷ passages du métier | 0 % | — | — | 61 | `n1_passages_coupes` |
| Erreur de lecture des scans (caractères) | caractères mal lus ÷ caractères des pages scannées retapées par le métier | 15 % | ≤ 2 % | ❌ non | 20 | `n1_erreur_caracteres` |
| Erreur de lecture des scans (mots) | mots mal lus ÷ mots des pages scannées retapées | 20 % | — | — | 20 | `n1_erreur_mots` |

### 2. Recherche

On vérifie que, pour chaque question, la recherche ramène les morceaux qui contiennent la réponse, et jamais un morceau d'un document interdit à la personne qui pose la question.

| Score | Ce qu'il compte | Résultat | Seuil | Atteint ? | Compté sur | Code |
| --- | --- | --- | --- | --- | --- | --- |
| Bon passage ramené | questions où un morceau contenant le passage du métier est parmi les k ramenés ÷ questions | 86 % ± 13 | ≥ 90 % | ❌ non | 28 | `n2_reussite_k` |
| Passages nécessaires ramenés | passages attendus parmi les k morceaux ramenés ÷ passages attendus | 81 % ± 12 | — | — | 42 | `n2_rappel_k` |
| Bon morceau en tête | 1 si le premier bon morceau est 1er, 1/2 s'il est 2e… ; moyenne | 68 % ± 17 | — | — | 28 | `n2_rang_premier` |
| Fuites de droits | questions où un morceau d'un document interdit au profil est ramené | 0 | ≤ 0 | ✅ oui | 40 | `n2_fuite_droits` |
| Bon passage ramené, si k = 1 | le même score, si la recherche ne ramenait qu'un morceau | 54 % ± 18 | — | — | 28 | `n2_reussite_1` |
| Bon passage ramené, si k = 3 | le même score, si la recherche ramenait 3 morceaux | 75 % ± 16 | — | — | 28 | `n2_reussite_3` |
| Bon passage ramené, si k = 5 | le même score, si la recherche ramenait 5 morceaux | 86 % ± 13 | — | — | 28 | `n2_reussite_5` |
| Pièges ou version périmée devant le bon | questions où un piège ou une ancienne version passe devant le bon morceau ÷ questions | 0 % | — | — | 28 | `n2_perimes_pieges` |

### 3. Réponse

On vérifie que la réponse écrite par le RAG est juste, qu'elle ne dit que ce que disent les documents, et que le RAG sait dire « je ne sais pas ».

| Score | Ce qu'il compte | Résultat | Seuil | Atteint ? | Compté sur | Code |
| --- | --- | --- | --- | --- | --- | --- |
| Réponses justes | juste = 1, partielle = 0,5, fausse = 0, selon le juge qui compare aux points clés du métier | 71 % ± 17 | ≥ 80 % | ❌ non | 29 | `n3_exactitude` |
| Listes complètes | éléments attendus présents dans la réponse ÷ éléments attendus | 100 % | — | — | 4 | `n3_completude_listes` |
| Chiffres exacts | valeurs attendues présentes dans la réponse, avec la bonne unité ÷ valeurs | 75 % ± 20 | — | — | 18 | `n3_valeurs` |
| Sait dire « je ne sais pas » | abstentions ÷ questions sans réponse dans les documents ou interdites au profil | 88 % ± 23 | ≥ 80 % | ✅ oui | 8 | `n3_abstention_correcte` |
| Abstentions à tort | abstentions alors que le bon passage était ramené ÷ questions | 3 % ± 6 | — | — | 32 | `n3_abstention_a_tort` |
| Fidélité aux documents | affirmations de la réponse appuyées par les morceaux ÷ affirmations | 95 % ± 8 | ≥ 90 % | ✅ oui | 30 | `n3_fidelite` |
| Bonnes sources citées | questions où une source citée contient le passage du métier, sans piège ni document interdit | 90 % ± 11 | — | — | 29 | `n3_citations` |
| Erreurs graves | réponses fausses, inventées ou données au lieu de s'abstenir, sur une question grave | 0 | ≤ 0 | ✅ oui | 11 | `n3_erreurs_graves` |
| Synthèses | note de 1 à 5 donnée par le juge sur une grille, ramenée sur 100 % | 73 % | — | — | 3 | `n3_synthese` |
| Questions de suite justes | même note que les réponses justes, sur les questions de suite | 67 % ± 53 | — | — | 3 | `n3_questions_suite` |
| Reformulations incohérentes | groupes de questions reformulées dont les réponses diffèrent ÷ groupes | 0 % | — | — | 6 | `n3_variantes` |

### 4. Bout en bout

On vérifie que le RAG est bon sur les questions qui comptent le plus, assez rapide et pas trop cher.

| Score | Ce qu'il compte | Résultat | Seuil | Atteint ? | Compté sur | Code |
| --- | --- | --- | --- | --- | --- | --- |
| Score pondéré | notes des réponses, chaque question pesant fréquence × gravité (de 1 à 9) | 77 % ± 13 | ≥ 80 % | ❌ non | 40 | `n4_score_pondere` |
| Erreurs graves | repris de l'évaluation de la réponse | 0 | ≤ 0 | ✅ oui | 11 | `n4_erreurs_graves` |
| Temps de réponse médian | la moitié des questions ont leur réponse en moins de ce temps | 0,9 s | ≤ 15,0 s | ✅ oui | 40 | `n4_temps_median` |
| Temps de réponse à 95 % | 95 % des questions ont leur réponse en moins de ce temps | 2,6 s | ≤ 30,0 s | ✅ oui | 40 | `n4_temps_p95` |
| Coût par question | coût moyen d'une réponse | 0,00 € | ≤ 0,05 € | ✅ oui | 40 | `n4_cout_moyen` |

## 3. Les questions à regarder en premier

Erreurs graves et fuites d'abord, puis réponses fausses, puis passages perdus à l'ingestion. Le détail de chaque question est dans `resultats_par_question.csv`.

| Question | Problème | Détail |
| --- | --- | --- |
| **Q-022** : quelle a été la durée totale des coupures sur le site A en 2025 ? | Réponse fausse | 1. absent : La réponse de l'assistant indique 142 minutes alors que le point clé exige 162 minutes. |
| **Q-023** : et pour le site B ? | Réponse fausse | 1. absent : La réponse de l'assistant mentionne le nombre de coupures (6) mais omet complètement la durée totale de 312 minutes. |
| **Q-030** : quelles interventions a-t-on faites sur l'armoire AD-A07, et qu'est-ce qui a été fait à chaque fois ? | Réponse fausse | 1. absent : La réponse mentionne une intervention sur les déclenchements mais ne précise pas la date (avril 2025) ni l'action spécifique (séparation du départ en deux circuits). ; 2. absent : La réponse mentionne un différentiel trop sensible sans indiquer la date (avril 2026) ni l'action de remplacement. |
| **Q-032** : combien de départs sont secourus par le groupe électrogène du site A ? | Réponse fausse | 1. absent : La réponse de l'assistant ne mentionne pas le chiffre '9', mais parle d'une 'partie' des départs sans précision quantitative. |
| **Q-038** : en combien d'années la compensation de l'énergie réactive du site A est-elle rentabilisée ? | Réponse fausse | 1. absent : La réponse de l'assistant ne mentionne pas le temps de rentabilisation (2,3 ans), se limitant aux données brutes d'investissement et d'économie annuelle. |
| **Q-041** : quels problèmes électriques reviennent le plus souvent dans les interventions des deux usines ? | Réponse fausse | 1. contredit : La réponse de référence mentionne des 'échauffements', tandis que l'assistant parle de 'desserrage' et de 'cosses défectueuses', ce qui sont des causes distinctes bien que liées. ; 2. absent : L'information concernant les défauts d'isolement sur le site B n'est pas mentionnée dans la réponse de l'assistant. ; 3. absent : L'information concernant les déclenchements intempestifs de di |
| **Q-044** : quelles sont les grandes différences entre les installations électriques du site A et du site B ? | Réponse fausse | 1. absent : La réponse ne mentionne ni le système TN-S pour le site A, ni le système IT pour le site B. ; 2. absent : La réponse ne précise pas le nombre de transformateurs (deux sur A, un seul sur B). ; 3. contredit : L'assistant affirme que le site B n'a pas d'onduleur centralisé mais possède des onduleurs locaux, alors que la référence indique simplement l'absence d'onduleur centralisé sans men |
| **Q-055** : tous les combien faut-il nettoyer les filtres d'aération des variateurs de vitesse ? | A répondu au lieu de s'abstenir | le RAG a répondu au lieu de s'abstenir |

## 4. La faute est-elle dans la recherche ou dans la réponse ?

Pour chaque question qui a une réponse dans les documents : le bon passage a-t-il été ramené, et la réponse est-elle juste ?

| Diagnostic | Questions | Que corriger |
| --- | --- | --- |
| tout va bien | 19 | — |
| génération : le bon morceau était retrouvé | 8 | le prompt ou le modèle de génération |
| recherche : le bon morceau n'est pas retrouvé | 4 | la lecture des documents, le découpage ou la recherche |
| génération : le bon morceau était retrouvé (abstention à tort) | 1 | le prompt ou le modèle de génération |

## 5. Par type de document

| Score | Compte rendu d'intervention | Note technique | Procédure | questions sans passage |
| --- | --- | --- | --- | --- |
| Passages du métier retrouvés | 100 % (n = 10) | 100 % (n = 27) | 100 % (n = 24) | — |
| Bon passage ramené | 50 % (n = 4) | 88 % (n = 16) | 100 % (n = 14) | — |
| Réponses justes | 60 % (n = 5) | 58 % (n = 18) | 94 % (n = 16) | — |
| Fidélité aux documents | 100 % (n = 5) | 93 % (n = 18) | 99 % (n = 16) | 67 % (n = 1) |
| Score pondéré | 36 % (n = 6) | 70 % (n = 20) | 89 % (n = 17) | 87 % (n = 7) |

## Les fichiers techniques de cette évaluation

Ce rapport en est tiré. On ne les ouvre que pour creuser.

| Fichier | Contenu |
| --- | --- |
| `scores.json` | tous les scores, avec leur marge d'erreur et leur détail par type de document, de question… |
| `resultats_par_question.csv` | une ligne par question et par score, avec la justification du juge : à ouvrir dans un tableur |
| `croisement.jsonl` | pour chaque question : bon passage ramené ou non, réponse juste ou non |
| `liens_index.jsonl` | chaque passage du métier et le morceau de la base où il a été retrouvé |
| `passages_non_rattaches.jsonl` | les passages du métier introuvables dans la base, avec leur cause probable |
| `relecture.jsonl` | les réponses que le métier doit relire, et pourquoi |
| `evaluation.json` | ce qui a été évalué : versions du corpus, du kit, du RAG, du juge, et les seuils |
