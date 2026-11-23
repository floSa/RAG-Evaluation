# Service d'évaluation, exemple

Ce dossier montre le [service d'évaluation](../service-evaluation/README.md) **une fois qu'il a tourné** sur le [RAG d'exemple](../service-rag-exemple/README.md). C'est **le même service, fichier pour fichier**, qui a en plus tourné : sa configuration, son corpus annoté et ses résultats sont remplis. Tout se lit ici, sans rien installer.

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

## Ce qu'on a fait, dans l'ordre

Les étapes de [la marche à suivre](../service-evaluation/documentation/integrer_votre_rag.md), faites pour de vrai. Toutes les commandes du service se lancent depuis ce dossier.

| Étape | Ce qu'on a fait | Ce que ça a produit |
| --- | --- | --- |
| **0. Installer le service** | copié `service-evaluation/` ici ; démarré Langfuse (`./initialiser.sh`, `docker compose up -d`) ; choisi pour juge le modèle `chat`, différent du modèle qui écrit les réponses du RAG | `uv run kit verifier-modeles` répond |
| **1. Construire et importer le corpus d'évaluation** | un corpus fictif, construit selon les règles du [guide 0a](documentation/0a_construction_du_corpus.md) ; les documents rangés dans [`corpus_annote/corpus_documentaire/`](corpus_annote/corpus_documentaire/), le fichier dans [`corpus_annote/`](corpus_annote/) ; puis `uv run kit importer corpus_annote/Corpus_evaluation_RAG.xlsx` | 50 documents et le fichier Excel rempli (60 questions, 97 passages, 20 pages scannées retapées) ; le corpus contrôlé, dans [`resultats/corpus/2026-11-20.1/`](resultats/corpus/) |
| **2. Fixer les seuils** | dans [`config/seuils.json`](config/seuils.json), avant toute évaluation | les seuils de la partie « Sur quoi se fonde la décision » |
| **3. Ouvrir les quatre endpoints du RAG au service** | le [RAG d'exemple](../service-rag-exemple/README.md) ouvre ses quatre endpoints dans `src/rag/endpoints_evaluation/` ; lancé avec `docker compose up -d --build` (dans `service-rag-exemple/`), à l'adresse http://127.0.0.1:8100, notée dans [`config/kit.yaml`](config/kit.yaml) ; vérifié avec `uv run kit appeler-rag` | « règle : respectée » |
| **4. Évaluer chaque configuration du RAG** | une évaluation par configuration. Pour chacune : relancer le RAG avec son réglage, puis `uv run kit evaluer`. Référence : `docker compose up -d` ; k = 3 : `RAG_K=3 docker compose up -d` ; sans réflexion : `sans_reflexion: true` dans `config/config.yaml` du RAG, puis `docker compose restart rag` ; hybride : `RAG_GRAPHE=true docker compose up -d` | les réponses du RAG dans [`resultats/reponses_du_rag/`](resultats/reponses_du_rag/), et un `RAPPORT.md` par configuration dans [`resultats/evaluations/`](resultats/evaluations/) |
| **5. Relire et comparer** | vérifié le juge : `uv run kit verifier-juge --envoyer`, puis les notes du métier (ici simulées : `uv run python corpus_annote/notes_du_metier_simulees/publier.py`), puis `uv run kit verifier-juge` ; comparé chaque configuration à la référence : `uv run kit comparer resultats/evaluations/<référence> resultats/evaluations/<autre>` | l'accord juge et métier : 89 %, pour 90 % exigés (juge à surveiller) ; les 3 rapports de comparaison dans [`resultats/comparaisons_de_configurations/`](resultats/comparaisons_de_configurations/) |

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

Les mêmes dossiers et les mêmes fichiers que dans `service-evaluation/`. Trois sont remplis, parce que le service a tourné :

| Dossier | Ce qu'il contient ici |
| --- | --- |
| [`config/`](config/) | nos réglages, et les seuils fixés par le métier |
| [`corpus_annote/`](corpus_annote/) | le corpus documentaire (50 documents) et le fichier Excel du métier rempli ; plus, pour ce banc d'essai seulement, les notes du métier simulées et le script qui a fabriqué les documents |
| [`resultats/`](resultats/) | le corpus contrôlé, les réponses du RAG pour chaque configuration, les 4 évaluations et les 3 comparaisons |
| [`endpoints_a_copier/`](endpoints_a_copier/), [`documentation/`](documentation/), [`src/`](src/), [`tests/`](tests/) | identiques à `service-evaluation/` : un test vérifie qu'ils le restent |

On peut donc aussi le faire tourner tel quel, depuis ce dossier, comme `service-evaluation/` : les commandes sont dans [son README](../service-evaluation/README.md#la-marche-à-suivre).

Chaque évaluation et chaque comparaison est un dossier nommé d'après la version du RAG évaluée. Exemple : `2026-11-20.1_graphrag-vectoriel-k5-5954e822` = le corpus du 20 novembre, le RAG « graphrag » en recherche vectorielle, avec k = 5, et une empreinte de ses autres réglages. Le tableau de la partie 1 dit à quelle configuration chacun correspond.
