# Service d'évaluation, exemple

Ce dossier montre le [service d'évaluation](../service-evaluation/README.md) **une fois qu'il a tourné** sur le [RAG d'exemple](../service-rag-exemple/README.md). C'est **le même service, fichier pour fichier**, qui a en plus tourné : sa configuration, son corpus annoté et ses résultats sont remplis. Tout se lit ici, sans rien installer.

## Ce qui a été évalué

**Le corpus** : 50 documents fictifs sur la maintenance électrique d'une entreprise inventée (procédures, notes techniques dont 5 scannées, et comptes rendus d'intervention, qui sont des fiches de GED exportées en PDF), et 60 questions écrites par le métier, avec leur bonne réponse et l'endroit des documents où elle se trouve. 40 questions servent à régler le RAG. Les 20 autres sont **réservées** : on ne les regarde jamais pendant les réglages, pour ne pas régler le RAG « pour l'examen » ; les scores clés, ceux présentés au métier, sont calculés sur elles.

**Le RAG** : le RAG d'exemple, dans trois configurations. Une configuration, c'est le RAG avec tous ses réglages fixés. La configuration de **référence** est celle de départ :

| Réglage | Valeur dans la référence | Ce que c'est |
| --- | --- | --- |
| Type de recherche | par vecteurs et par mots-clés | le RAG compare le sens de la question à celui de chaque morceau de texte, grâce à des vecteurs, et cherche aussi ses mots exacts ; il n'a pas de graphe |
| Nombre de morceaux ramenés (k) | 5 | pour chaque question, la recherche ramène 5 morceaux, que le modèle lit pour écrire sa réponse |
| Découpage | par section | chaque document est coupé en morceaux qui suivent ses titres |
| Modèle de génération | gemma-4-e4b, avec réflexion | le modèle qui écrit la réponse ; « avec réflexion » : il raisonne avant de répondre |

Les deux autres configurations changent **un seul réglage** chacune, pour mesurer son effet :

| Configuration | Le réglage changé |
| --- | --- |
| k = 3 | la recherche ramène 3 morceaux au lieu de 5 |
| Sans réflexion | le modèle écrit sa réponse directement, sans raisonner d'abord |

## Ce qu'on a fait, dans l'ordre

Les étapes du [fil conducteur](../service-evaluation/FIL_CONDUCTEUR.md), faites pour de vrai. Toutes les commandes du service se lancent depuis ce dossier.

| Étape | Ce qu'on a fait | Ce que ça a produit |
| --- | --- | --- |
| **0. Installer le service d'évaluation** | copié `service-evaluation/` ici ; démarré Langfuse (`./initialiser.sh`, `docker compose up -d`) ; choisi pour juge le modèle `chat`, différent du modèle qui écrit les réponses du RAG | `uv run kit verifier-modeles` répond |
| **1. Construire et importer le corpus d'évaluation** | un corpus fictif, construit selon les règles de [0a. Construction du corpus](documentation/0a_construction_du_corpus.md) ; les documents rangés dans [`corpus_annote/corpus_documentaire/`](corpus_annote/corpus_documentaire/), le fichier dans [`corpus_annote/`](corpus_annote/) ; puis `uv run kit importer corpus_annote/Corpus_evaluation_RAG.xlsx` | 50 documents et le fichier Excel rempli (60 questions, 97 passages, 20 pages scannées retapées) ; le corpus contrôlé, dans [`resultats/corpus/2026-11-20.1/`](resultats/corpus/) |
| **2. Ouvrir les quatre endpoints du RAG au service** | le [RAG d'exemple](../service-rag-exemple/README.md) ouvre ses quatre endpoints dans `src/rag/endpoints_evaluation/` ; lancé avec `docker compose up -d --build` (dans `service-rag-exemple/`), à l'adresse http://127.0.0.1:8100, notée dans [`config/kit.yaml`](config/kit.yaml) ; vérifié avec `uv run kit appeler-rag` | « règle : respectée » |
| **3. Évaluer une configuration du RAG** | une évaluation par configuration. Pour chacune : relancer le RAG avec son réglage, puis `uv run kit evaluer`. Référence : `docker compose up -d` ; k = 3 : `RAG_K=3 docker compose up -d` ; sans réflexion : `sans_reflexion: true` dans `config/config.yaml` du RAG, puis `docker compose restart rag` | les réponses du RAG dans [`resultats/reponses_du_rag/`](resultats/reponses_du_rag/), et un `RAPPORT.md` par configuration dans [`resultats/evaluations/`](resultats/evaluations/) |
| **4. Lire le rapport, comparer, faire décider le métier** | vérifié le juge : `uv run kit verifier-juge --preparer` écrit le fichier Excel à faire noter par le métier ; ici, les notes sont simulées (`uv run python corpus_annote/notes_du_metier_simulees/publier.py`) ; puis `uv run kit verifier-juge` ; comparé chaque configuration à la référence : `uv run kit comparer resultats/evaluations/<référence> resultats/evaluations/<autre>` | le juge n'est pas validé : il donne la même note que le métier dans 89 % des cas, il en faut 90 % ; les 3 rapports de comparaison dans [`resultats/comparaisons_de_configurations/`](resultats/comparaisons_de_configurations/) |

## 1. Les trois configurations évaluées

Chaque rapport donne les scores, chacun en une phrase. Le service ne décide pas : c'est au métier de trancher. Ci-dessous, quelques chiffres pour situer les configurations, sur les 40 questions de réglage.

| Configuration | Réponses justes | Score pondéré | Erreurs graves | Rapport |
| --- | --- | --- | --- | --- |
| **Référence** | 79 % | 80 % | 1 | [lire](resultats/evaluations/2026-11-20.1_graphrag-vectoriel-k5-5954e822/RAPPORT.md) |
| k = 3 | 83 % | 77 % | 0 | [lire](resultats/evaluations/2026-11-20.1_graphrag-vectoriel-k3-5954e822/RAPPORT.md) |
| Sans réflexion | 71 % | 77 % | 0 | [lire](resultats/evaluations/2026-11-20.1_graphrag-vectoriel-k5-94d362c8/RAPPORT.md) |

- **Réponses justes** : un modèle juge compare chaque réponse à la bonne réponse du métier. Une réponse juste compte 1, une réponse partielle 0,5, une réponse fausse 0.
- **Score pondéré** : la même note, mais chaque question compte selon sa fréquence et sa gravité, fixées par le métier. C'est le chiffre le plus proche de ce que vivront les utilisateurs.
- **Erreurs graves** : réponses fausses ou inventées à une question que le métier a jugée grave.

**Ce qu'on présenterait au métier.** Les trois configurations butent sur les mêmes points :
- les pages scannées sont mal lues : 15 caractères sur 100 sont faux ;
- la recherche ne ramène pas assez souvent le bon passage : pour 9 questions réservées sur 13 seulement, dans la référence.

Il vaut mieux corriger ces deux points avant de lui demander de décider.

## 2. Les deux comparaisons avec la référence

| Comparaison | Ce qu'on en conclut | Rapport |
| --- | --- | --- |
| Référence contre **k = 3** | **Pas meilleure.** Avec 3 morceaux, la recherche ramène moins souvent le bon passage (75 % contre 86 %) : 3 questions perdues (Q-031, Q-038, Q-057), aucune gagnée. Elle n'a plus d'erreur grave, mais seulement parce qu'elle ne répond pas à la question en cause (Q-046). | [lire](resultats/comparaisons_de_configurations/2026-11-20.1_graphrag-vectoriel-k5-5954e822_contre_graphrag-vectoriel-k3-5954e822/RAPPORT.md) |
| Référence contre **sans réflexion** | **On garde la réflexion.** Sans elle, le RAG répond 8 fois plus vite (0,9 s contre 7,4 s), mais calcule moins bien : 75 % de chiffres exacts contre 91 %. L'écart reste dans la marge, donc non prouvé à lui seul, mais trois calculs sont perdus (Q-022, Q-023, Q-038). Avec la réflexion, une réponse prend 7,4 s. | [lire](resultats/comparaisons_de_configurations/2026-11-20.1_graphrag-vectoriel-k5-5954e822_contre_graphrag-vectoriel-k5-94d362c8/RAPPORT.md) |

## Ce qu'il y a dans ce dossier

Les mêmes dossiers et les mêmes fichiers que dans `service-evaluation/`. Trois sont remplis, parce que le service a tourné :

| Dossier | Ce qu'il contient ici |
| --- | --- |
| [`config/`](config/) | nos réglages : le modèle juge et l'adresse du RAG |
| [`corpus_annote/`](corpus_annote/) | le corpus documentaire (50 documents) et le fichier Excel du métier rempli ; plus, pour ce banc d'essai seulement, les notes du métier simulées et le script qui a fabriqué les documents |
| [`resultats/`](resultats/) | le corpus contrôlé, les réponses du RAG pour chaque configuration, les 3 évaluations et les 2 comparaisons |
| [`endpoints_a_copier/`](endpoints_a_copier/), [`documentation/`](documentation/), [`src/`](src/), [`tests/`](tests/) | identiques à `service-evaluation/` : un test vérifie qu'ils le restent |

On peut donc aussi le faire tourner tel quel, depuis ce dossier, comme `service-evaluation/` : les étapes sont dans le [fil conducteur](../service-evaluation/FIL_CONDUCTEUR.md), et les commandes dans [le README du service](../service-evaluation/README.md#toutes-les-commandes).

Chaque évaluation et chaque comparaison est un dossier nommé d'après la version du RAG évaluée. Exemple : `2026-11-20.1_graphrag-vectoriel-k5-5954e822` = le corpus du 20 novembre, le RAG « graphrag » en recherche vectorielle, avec k = 5, et une empreinte de ses autres réglages. Le tableau de la partie 1 dit à quelle configuration chacun correspond.
