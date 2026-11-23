# Évaluation de la configuration `graphrag-vectoriel-k3-5954e822`

Ce rapport évalue **une configuration** du RAG sur le corpus du métier. Il répond à une question : **cette configuration peut-elle partir en production ?**

|  |  |
| --- | --- |
| Configuration évaluée | RAG vectoriel, k = 3, découpage sections-1, embeddings embed, génération gemma-4-e4b, prompt 1.0, reranker aucun |
| Corpus | version 2026-11-20.1 : 60 questions, dont 20 réservées à la décision |
| Juge | chat, prompt 1.0 |

## 1. La décision

**❌ Mise en production non recommandée.**

- Seuil(s) non atteint(s) : Erreur de lecture des scans (caractères), Bon passage ramené, Score pondéré.

Les seuils sont fixés par le métier avant l'évaluation. Ils se jugent sur les 20 questions réservées à la décision, jamais utilisées pour régler le RAG. Les critères bloquants (fuite de droits, erreur grave) se jugent sur toutes les questions.

| Ce qui est vérifié | Résultat | Seuil | Atteint ? | Compté sur |
| --- | --- | --- | --- | --- |
| Documents présents dans la base | 100 % | ≥ 100 % | ✅ oui | 50 |
| Étiquettes complètes | 100 % | ≥ 100 % | ✅ oui | 534 |
| Passages du métier retrouvés | 100 % | ≥ 95 % | ✅ oui | 30 |
| Erreur de lecture des scans (caractères) | 15 % | ≤ 2 % | ❌ non | 20 |
| Bon passage ramené | 62 % ± 26 | ≥ 90 % | ❌ non | 13 |
| Fuites de droits | 0 | ≤ 0 | ✅ oui | 60 |
| Réponses justes | 82 % ± 23 | ≥ 80 % | ✅ oui | 11 |
| Sait dire « je ne sais pas » | 100 % | ≥ 80 % | ✅ oui | 5 |
| Fidélité aux documents | 100 % | ≥ 90 % | ✅ oui | 11 |
| Erreurs graves | 0 | ≤ 0 | ✅ oui | 12 |
| Score pondéré | 74 % ± 19 | ≥ 80 % | ❌ non | 20 |
| Temps de réponse médian | 6,8 s | ≤ 15,0 s | ✅ oui | 20 |
| Temps de réponse à 95 % | 11,0 s | ≤ 30,0 s | ✅ oui | 20 |
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
| Bon passage ramené | questions où un morceau contenant le passage du métier est parmi les k ramenés ÷ questions | 75 % ± 16 | ≥ 90 % | ❌ non | 28 | `n2_reussite_k` |
| Passages nécessaires ramenés | passages attendus parmi les k morceaux ramenés ÷ passages attendus | 64 % ± 14 | — | — | 42 | `n2_rappel_k` |
| Bon morceau en tête | 1 si le premier bon morceau est 1er, 1/2 s'il est 2e… ; moyenne | 65 % ± 18 | — | — | 28 | `n2_rang_premier` |
| Fuites de droits | questions où un morceau d'un document interdit au profil est ramené | 0 | ≤ 0 | ✅ oui | 40 | `n2_fuite_droits` |
| Bon passage ramené, si k = 1 | le même score, si la recherche ne ramenait qu'un morceau | 54 % ± 18 | — | — | 28 | `n2_reussite_1` |
| Bon passage ramené, si k = 3 | le même score, si la recherche ramenait 3 morceaux | 75 % ± 16 | — | — | 28 | `n2_reussite_3` |
| Pièges ou version périmée devant le bon | questions où un piège ou une ancienne version passe devant le bon morceau ÷ questions | 0 % | — | — | 28 | `n2_perimes_pieges` |

### 3. Réponse

On vérifie que la réponse écrite par le RAG est juste, qu'elle ne dit que ce que disent les documents, et que le RAG sait dire « je ne sais pas ».

| Score | Ce qu'il compte | Résultat | Seuil | Atteint ? | Compté sur | Code |
| --- | --- | --- | --- | --- | --- | --- |
| Réponses justes | juste = 1, partielle = 0,5, fausse = 0, selon le juge qui compare aux points clés du métier | 83 % ± 15 | ≥ 80 % | ✅ oui | 23 | `n3_exactitude` |
| Listes complètes | éléments attendus présents dans la réponse ÷ éléments attendus | 100 % | — | — | 3 | `n3_completude_listes` |
| Chiffres exacts | valeurs attendues présentes dans la réponse, avec la bonne unité ÷ valeurs | 97 % ± 9 | — | — | 15 | `n3_valeurs` |
| Sait dire « je ne sais pas » | abstentions ÷ questions sans réponse dans les documents ou interdites au profil | 100 % | ≥ 80 % | ✅ oui | 8 | `n3_abstention_correcte` |
| Abstentions à tort | abstentions alors que le bon passage était ramené ÷ questions | 6 % ± 8 | — | — | 32 | `n3_abstention_a_tort` |
| Fidélité aux documents | affirmations de la réponse appuyées par les morceaux ÷ affirmations | 97 % ± 7 | ≥ 90 % | ✅ oui | 23 | `n3_fidelite` |
| Bonnes sources citées | questions où une source citée contient le passage du métier, sans piège ni document interdit | 91 % ± 12 | — | — | 23 | `n3_citations` |
| Erreurs graves | réponses fausses, inventées ou données au lieu de s'abstenir, sur une question grave | 0 | ≤ 0 | ✅ oui | 11 | `n3_erreurs_graves` |
| Synthèses | note de 1 à 5 donnée par le juge sur une grille, ramenée sur 100 % | 67 % | — | — | 3 | `n3_synthese` |
| Questions de suite justes | même note que les réponses justes, sur les questions de suite | 100 % | — | — | 3 | `n3_questions_suite` |
| Reformulations incohérentes | groupes de questions reformulées dont les réponses diffèrent ÷ groupes | 0 % | — | — | 6 | `n3_variantes` |

### 4. Bout en bout

On vérifie que le RAG est bon sur les questions qui comptent le plus, assez rapide et pas trop cher.

| Score | Ce qu'il compte | Résultat | Seuil | Atteint ? | Compté sur | Code |
| --- | --- | --- | --- | --- | --- | --- |
| Score pondéré | notes des réponses, chaque question pesant fréquence × gravité (de 1 à 9) | 77 % ± 13 | ≥ 80 % | ❌ non | 40 | `n4_score_pondere` |
| Erreurs graves | repris de l'évaluation de la réponse | 0 | ≤ 0 | ✅ oui | 11 | `n4_erreurs_graves` |
| Temps de réponse médian | la moitié des questions ont leur réponse en moins de ce temps | 6,7 s | ≤ 15,0 s | ✅ oui | 40 | `n4_temps_median` |
| Temps de réponse à 95 % | 95 % des questions ont leur réponse en moins de ce temps | 10,9 s | ≤ 30,0 s | ✅ oui | 40 | `n4_temps_p95` |
| Coût par question | coût moyen d'une réponse | 0,00 € | ≤ 0,05 € | ✅ oui | 40 | `n4_cout_moyen` |

## 3. Les questions à regarder en premier

Erreurs graves et fuites d'abord, puis réponses fausses, puis passages perdus à l'ingestion. Le détail de chaque question est dans `resultats_par_question.csv`.

| Question | Problème | Détail |
| --- | --- | --- |
| **Q-041** : quels problèmes électriques reviennent le plus souvent dans les interventions des deux usines ? | Réponse fausse | 1. contredit : La réponse de référence mentionne des échauffements relevés en thermographie, tandis que l'assistant identifie le desserrage comme la cause première, ce qui est une affirmation incompatible sans preuve dans le contexte fourni. ; 2. absent : Le défaut d'isolement spécifique au site B n'est pas mentionné dans la réponse de l'assistant. ; 3. absent : Les déclenchements intempestifs de  |
| **Q-043** : quels enseignements tirer des campagnes de thermographie depuis 2023 ? | Réponse fausse | 1. absent : L'assistant mentionne le desserrage des connexions mais ne précise pas qu'il s'agit de la 'première cause', contrairement à la référence. ; 2. absent : L'assistant ne cite aucun point chaud récurrent spécifique (TGBT-A ou AD-B04). ; 3. contredit : L'assistant indique que la périodicité est passée de 24 à 12 mois en 2025, alors que la référence précise que le changement s'est produit de |
| **Q-044** : quelles sont les grandes différences entre les installations électriques du site A et du site B ? | Réponse fausse | 1. absent : La réponse ne mentionne ni le système TN-S pour le site A, ni le système IT pour le site B. ; 2. absent : La réponse ne précise pas le nombre de transformateurs (deux sur A, un seul sur B). ; 3. contredit : L'assistant affirme que le site B n'a pas d'onduleur centralisé mais possède des onduleurs locaux, alors que la référence indique simplement l'absence d'onduleur centralisé sans men |

## 4. La faute est-elle dans la recherche ou dans la réponse ?

Pour chaque question qui a une réponse dans les documents : le bon passage a-t-il été ramené, et la réponse est-elle juste ?

| Diagnostic | Questions | Que corriger |
| --- | --- | --- |
| tout va bien | 17 | — |
| recherche : le bon morceau n'est pas retrouvé | 7 | la lecture des documents, le découpage ou la recherche |
| génération : le bon morceau était retrouvé | 5 | le prompt ou le modèle de génération |
| génération : le bon morceau était retrouvé (abstention à tort) | 2 | le prompt ou le modèle de génération |
| juste sans le bon morceau : connaissance du modèle, ou passage manquant au corpus | 1 | — |

## 5. Par type de document

| Score | Compte rendu d'intervention | Note technique | Procédure | questions sans passage |
| --- | --- | --- | --- | --- |
| Passages du métier retrouvés | 100 % (n = 10) | 100 % (n = 27) | 100 % (n = 24) | — |
| Bon passage ramené | 25 % (n = 4) | 75 % (n = 16) | 93 % (n = 14) | — |
| Réponses justes | 0 % (n = 2) | 73 % (n = 15) | 88 % (n = 16) | — |
| Fidélité aux documents | 92 % (n = 2) | 96 % (n = 15) | 97 % (n = 16) | — |
| Score pondéré | 0 % (n = 6) | 69 % (n = 20) | 86 % (n = 17) | 100 % (n = 7) |

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
| `evaluation.json` | ce qui a été évalué : versions du corpus, du kit, du RAG, du juge, et les seuils |
