# Décisions et écarts

Les documents de référence décrivent la méthode : le [document 1](service-evaluation/documentation/methode_et_contrat/methode_corpus_annote.md) (le corpus annoté), le [document 2](service-rag-exemple/documentation/reference/techniques_rag.md) (les techniques d'un RAG), le [document 3](service-evaluation/documentation/methode_et_contrat/methode_evaluation.md) (l'évaluation), le [contrat](service-evaluation/documentation/methode_et_contrat/contrat_des_fichiers.md) et le [prompt du juge](service-evaluation/documentation/methode_et_contrat/prompt_du_juge.md).

Quand une décision prise ensemble change la façon de faire, ils sont mis à jour pour la dire : c'est le cas de les endpoints d'évaluation, qui a remplacé le connecteur.

Quand ils laissent un choix ouvert, ou quand la mise en œuvre s'en écarte, la décision est écrite ici, avec sa raison. Dans `CLAUDE.md`, les anciens noms `RAG_1_…`, `RAG_2_…`, `RAG_3_…`, `CONTRAT.md`, `JUGE.md` et `Corpus_evaluation_RAG.xlsx` désignent ces mêmes documents et le [modèle vierge](service-evaluation/corpus_annote/Corpus_evaluation_RAG.xlsx).

## 1. Décisions sur les points que la méthode laisse ouverts

| # | Point | Ce que disent les documents | Décision |
| --- | --- | --- | --- |
| 1 | Identifiant d'un passage | « numéro de ligne », « stable d'une version à l'autre tant que la ligne ne change pas » ; or une ligne insérée plus haut décale les numéros | premier import : `passage_id` = numéro de la ligne Excel. Ensuite, une ligne identique (question, document, page, type, passage, répond) garde son identifiant ; une ligne nouvelle ou modifiée reçoit un identifiant jamais utilisé |
| 2 | Réponse « non fidèle » dans les erreurs graves | aucun seuil par question | non fidèle = **au moins une affirmation non appuyée** (fidélité Ragas < 1,0), réglable (`seuil_non_fidele` dans `kit.yaml`). C'est la règle de Lynx, RAGTruth, Azure Groundedness Pro et DeepEval en mode strict ; le seuil de 0,5 des outils est trop laxiste pour une question à risque. Chaque cas est relu par le métier |
| 3 | Score pondéré : questions sans réponse | « somme des poids des réponses justes » | question sans réponse ou interdite : juste si le RAG s'abstient, fausse sinon ; question avec réponse où le RAG s'abstient : fausse. Règle de CRAG (2024) et SQuAD 2.0, sans la pénalité négative de CRAG |
| 4 | Marge d'erreur | formule écrite pour une proportion | appliquée aux scores entre 0 et 1 (pour une moyenne de valeurs entre 0 et 1, la variance est au plus p(1−p) : la marge est prudente) ; pas de marge pour les nombres, temps et coûts. La formule ne sait pas estimer l'incertitude à 0 % et 100 % : l'intervalle de Wilson ou le rééchantillonnage relèvent de la configuration recommandée |
| 5 | Questions réservées | « l'équipe technique n'en voit que les scores globaux » | le détail du rapport, le CSV, Langfuse et les scores de `scores.json` portent sur les questions non réservées. Les scores clés, en tête du rapport et dans le bloc `scores_cles`, sont calculés sur les questions réservées, sans détail ; les fuites de droits et les erreurs graves, sur toutes les questions. Le détail des réservées reste dans la base |
| 6 | Coût | en euros | prix au million de tokens d'entrée et de sortie dans la configuration du RAG ; 0 pour un modèle local. Générique, quel que soit le fournisseur |
| 7 | Fiche de GED | « page » = nom du champ (document 1) ; « un chunk par fiche » (document 2) | le rattachement accepte un chunk du même document dont la page est le nom du champ, **ou** dont le texte contient ce nom : un RAG qui fait un chunk par fiche est donc bien évalué. Le RAG d'exemple fait un chunk par champ |
| 8 | Taille du corpus d'exemple | `CLAUDE.md` : 12 documents, 30 questions ; document 1, configuration minimale : 10 documents par type, 50 questions, 20 pages OCR | **la configuration minimale du document 1 est atteinte** : 50 documents, 60 questions, 20 pages OCR. Un banc d'essai qui servira à d'autres doit être réaliste |
| 9 | Juge et RAG | « de préférence un autre modèle » | RAG : `gemma-4-e4b` ; juge et Ragas : `chat` (qwen3.5-4b), réflexion désactivée ; embeddings : `embed` (bge-m3) |
| 10 | Vérification du juge | accord d'au moins 90 % | appliqué tel quel ; le kit affiche aussi le kappa de Cohen, qui repère un juge qui dit presque toujours « juste » (Thakur et al., 2024) |
| 11 | Comparaison de deux versions | McNemar en configuration recommandée | fait : test exact, sans dépendance |
| 12 | Rattachement approché d'un texte | « il lui ressemble à 95 % » | ressemblance entre le passage et la partie du chunk qui lui ressemble le plus ; si le chunk est plus court que le passage, on compare les deux textes entiers (sinon un chunk qui ne porte que la moitié du passage passerait) |
| 13 | Une ligne fausse dans le fichier Excel | « rejet de la ligne, avec un message clair » | toutes les lignes fausses sont listées, et **rien n'est importé** tant qu'il en reste une : un corpus à moitié importé fausserait l'évaluation sans que personne ne s'en aperçoive |
| 14 | Seuils et décision de mise en production | des seuils par score, fixés avec le métier, et une décision automatique | **pas de seuils, pas de décision automatique** : le service donne les scores, chacun écrit en une phrase compréhensible par le métier (« pour 9 questions sur 13, la recherche ramène le passage qui contient la réponse »), et c'est le métier qui tranche à leur lecture. Un seuil fixé à l'avance se discute mal : le métier juge mieux devant les chiffres et les questions ratées |
| 15 | Fiches de GED | les documents sont des fichiers ; « fiche de base de données » : page = nom du champ | une source peut être un fichier ou une **fiche de GED** (fiche, ticket, compte rendu d'une base documentaire), dans le même corpus. Le métier repère une fiche par sa GED (colonne Source), son numéro affiché (Référence) et le nom du champ affiché (Page) ; une pièce jointe est une source à part ; le corpus porte sur une copie figée de la GED. Le libellé « Fiche de base de données » devient « Fiche de GED » (l'ancien reste accepté, le code `fiche_base` ne change pas). Une fiche sans fichier est envoyée au RAG par sa seule référence, et le RAG la lit dans sa GED ; exportée en `<référence>.pdf`, elle est envoyée comme un fichier |

## 2. Écarts avec les consignes de mise en œuvre (`CLAUDE.md`)

| Écart | Raison |
| --- | --- |
| Trois dossiers à la racine : `service-evaluation/` (le service, vierge), `service-rag-exemple/` (le RAG d'exemple) et `service-evaluation-exemple/` (le même service, rempli après avoir tourné sur ce RAG), au lieu de `kit/`, `rag_demo/`, `corpus_exemple/` et `sorties/` | on voit tout de suite ce qui est le service et ce qui est la démonstration ; on prend le service pour son projet sans emporter nos données ; l'exemple montre exactement ce que le service produit. Chaque dossier a son README. Les noms disent ce que contient le dossier : `corpus_annote/corpus_documentaire/` (ce que le RAG lit, pas seulement des documents), `resultats/evaluations/` et `resultats/comparaisons_de_configurations/` (évaluer une configuration n'est pas comparer deux configurations) |
| Deux services indépendants, `service-rag-exemple/` et `service-evaluation/`, chacun avec son README, sa documentation, son `docker-compose.yml`, ses tests et son installation | le produit, c'est le service d'évaluation : il impose à tout RAG quatre endpoints de forme fixe (voir le README). Les guides et le code du kit portent le même nom d'étape : `etape_0a_corpus` … `etape_5_resultats` |
| Commandes `kit evaluer-ingestion`, `evaluer-recherche`, `evaluer-reponse`, `evaluer-bout-en-bout` au lieu de `kit niveau1` à `kit niveau4` | le nom dit ce qui est évalué. Les niveaux 1 à 4 du document 3 restent dans les préfixes des scores (`n1_` à `n4_`) |
| Le RAG est évalué par **quatre endpoints, à une adresse web** (ingérer, montrer l'index, rechercher, répondre), et non par un connecteur Python | n'importe quel RAG, dans n'importe quel langage, ouvre les mêmes endpoints. Le service d'évaluation envoie lui-même ses documents : il sait exactement ce que le RAG a reçu, ce qui compte pour évaluer l'ingestion. Le RAG les range à part de la production, et ne reçoit jamais les annotations |
| L'ontologie du domaine est à deux endroits : dans le RAG (`service-rag-exemple/config/ontologie.ttl`), pour extraire son graphe, et dans le service d'évaluation (`service-evaluation-exemple/corpus_annote/ontologie/`), avec ses règles SHACL, dont le kit lit le chemin dans `kit.yaml` (`graphe.formes`) | le contrat dit que « le projet fournit à côté `ontologie_formes.ttl` » : les règles appartiennent au projet, pas au RAG, qui ne doit pas fournir lui-même ce qui le contrôle |
| Le graphe entre dans l'index comme des éléments `noeud` (un par entité et par page, qui résume ses relations sur la page), et non comme un élément par relation | le contrat donne k éléments par recherche : un élément qui réunit les relations d'une entité en apporte plus au modèle pour la même place ; il garde la provenance d'une page, donc le filtre des droits et les citations marchent comme pour un chunk |
| Un passage coupé se cherche entre deux chunks de texte consécutifs, sans les éléments du graphe | un élément du graphe n'est pas un morceau du document : il casserait la suite des chunks |
| La version du RAG s'appelle `graphrag-<type_rag>-k<k>-<empreinte>` | on lit dans le nom si le graphe était allumé. `graphrag` n'est que le `nom` donné dans `config.yaml` : le RAG d'exemple est vectoriel par défaut. Le changer changerait le nom de toutes les évaluations citées dans les guides |
| Dans le banc d'essai, la relecture du métier (vérification du juge, justesse du graphe) est simulée par Claude, et ses notes sont versionnées dans `service-evaluation-exemple/corpus_annote/notes_du_metier_simulees/` | l'entreprise est fictive : il n'y a pas de métier réel. Les notes sont données sans voir la note du juge, avec leur raison, pour qu'on puisse les contester. Résultat : accord du juge 89 %, sous le seuil de 90 % (trois réponses que le juge dit « fausses » à tort) ; le juge n'est pas validé, et on ne retouche pas les notes pour le faire passer |
| Le modèle de génération du RAG d'exemple garde sa réflexion, avec `max_tokens` à 4 000 au lieu de 800 | avec 800, la réflexion consommait la place de la réponse : trois réponses vides ou coupées. Couper la réflexion corrigeait aussi, 9 fois plus vite, mais faisait perdre trois calculs (comparaison dans le guide 5) |
| Docling (conteneur) au lieu de `pytesseract` pour l'OCR du RAG d'exemple | rien à installer sur la machine ; c'est l'outil cité par le document 2. Le kit n'en dépend pas : il mesure l'OCR de n'importe quel RAG avec jiwer |
| Pas de modèle de vision dans le RAG d'exemple : une figure est connue par sa légende | le RAG est un prétexte ; le kit montre la perte (question Q-034) |
| Langfuse v4 au lieu de v3 | v3 n'est plus la version courante ; le client Python actuel exige v4 |
| Expérience Langfuse créée en rejouant les réponses du RAG (`run_experiment`), au lieu de relier les traces du RAG au jeu de données | Langfuse v4 ne permet plus de relier une trace existante à un jeu de données. Chaque ligne de l'expérience garde l'identifiant de la trace du RAG (`trace_rag`) |
| La table `resultats` a quatre colonnes de plus (objet évalué, axes de ventilation, poids, réservée) ; une table `corpus` en plus | recalculer tous les scores et leurs ventilations depuis la base, niveau par niveau |
| Fichiers en plus dans `resultats/` : `passages_non_rattaches.jsonl`, `croisement.jsonl`, `relecture.jsonl`, `langfuse.json` | la liste des passages non rattachés est demandée à l'étape 5 ; le croisement à l'étape 7 |
| `openai` < 3 | exigé par Ragas 0.4 (par sa dépendance `instructor`) |

## 3. Ce qui n'est pas fait (configuration recommandée, ou étape suivante)

| Point | État |
| --- | --- |
| `n2_ndcg_k` (ranx), `n3_second_avis` (FactualCorrectness), marge par rééchantillonnage | configuration recommandée ; non faits |
| GraphRAG au sens de Microsoft (communautés et résumés, type_objet `resume`) | non fait : le graphe d'exemple relie des entités, il ne résume pas le corpus |

## 4. Environnement du bac à sable

| Élément | Choix |
| --- | --- |
| Modèles | LLM-Service (LiteLLM local, `http://127.0.0.1:8080/v1`) ; une clé pour le kit, une pour le RAG |
| Langfuse | auto-hébergé, v4, port 3100 (`service-evaluation/docker-compose.yml`) |
| Docling | conteneur `docling-serve-cpu`, port 5101 (`service-rag-exemple/docker-compose.yml`) |
| Python | 3.12, géré par uv ; deux projets indépendants, installés chacun dans son dossier (`service-evaluation/` : commande `kit` ; `service-rag-exemple/` : commande `rag`). Le RAG tourne aussi en conteneur, sa endpoint ouvert à http://127.0.0.1:8100 |
| Licences | uniquement MIT, Apache 2.0, BSD : reportlab, pypdfium2, Pillow, pypdf, rank-bm25, numpy, openai, jsonschema, rapidfuzz, jiwer, ragas, langfuse, typer, SQLAlchemy, openpyxl |
