# Décisions et écarts

Les documents de référence ([document 1](service-evaluation/documentation/reference/methode_corpus_annote.md), [document 2](service-rag/documentation/reference/techniques_rag.md), [document 3](service-evaluation/documentation/reference/methode_evaluation.md), le [contrat](service-evaluation/documentation/reference/contrat_des_fichiers.md), le [prompt du juge](service-evaluation/documentation/reference/prompt_du_juge.md)) décrivent la méthode. Quand une décision prise ensemble change la façon de faire, ils sont mis à jour pour la dire (c'est le cas de la porte d'évaluation, qui a remplacé le connecteur). Leurs noms de fichiers ont changé pour dire ce qu'ils contiennent : dans leur texte, `RAG_1_…`, `RAG_2_…`, `RAG_3_…`, `CONTRAT.md`, `JUGE.md` et `Corpus_evaluation_RAG.xlsx` désignent respectivement `methode_corpus_annote.md`, `techniques_rag.md`, `methode_evaluation.md`, `contrat_des_fichiers.md`, `prompt_du_juge.md` et `modele_corpus_vierge.xlsx`. Quand ils laissent un choix ouvert, ou quand la mise en œuvre s'en écarte, la décision est écrite ici, avec sa raison.

## 1. Décisions sur les points que la méthode laisse ouverts

| # | Point | Ce que disent les documents | Décision |
| --- | --- | --- | --- |
| 1 | Identifiant d'un passage | « numéro de ligne », « stable d'une version à l'autre tant que la ligne ne change pas » ; or une ligne insérée plus haut décale les numéros | premier import : `passage_id` = numéro de la ligne Excel. Ensuite, une ligne identique (question, document, page, type, passage, répond) garde son identifiant ; une ligne nouvelle ou modifiée reçoit un identifiant jamais utilisé |
| 2 | Réponse « non fidèle » dans les erreurs graves | aucun seuil par question | non fidèle = **au moins une affirmation non appuyée** (fidélité Ragas < 1,0), réglable (`seuil_non_fidele` dans `kit.yaml`). C'est la règle de Lynx, RAGTruth, Azure Groundedness Pro et DeepEval en mode strict ; le seuil de 0,5 des outils est trop laxiste pour une question à risque. Chaque cas est relu par le métier |
| 3 | Score pondéré : questions sans réponse | « somme des poids des réponses justes » | question sans réponse ou interdite : juste si le RAG s'abstient, fausse sinon ; question avec réponse où le RAG s'abstient : fausse. Règle de CRAG (2024) et SQuAD 2.0, sans la pénalité négative de CRAG |
| 4 | Marge d'erreur | formule écrite pour une proportion | appliquée aux scores entre 0 et 1 (pour une moyenne de valeurs entre 0 et 1, la variance est au plus p(1−p) : la marge est prudente) ; pas de marge pour les nombres, temps et coûts. La formule ne sait pas estimer l'incertitude à 0 % et 100 % : l'intervalle de Wilson ou le rééchantillonnage relèvent de la configuration recommandée |
| 5 | Questions réservées à la décision | « l'équipe technique n'en voit que les scores globaux » | le rapport, le CSV, Langfuse et les scores de `scores.json` portent sur les questions non réservées. Le bloc `decision` donne les scores des questions réservées, sans détail. Les critères bloquants se jugent sur toutes les questions. Le détail des réservées reste dans la base |
| 6 | Coût | en euros | prix au million de tokens d'entrée et de sortie dans la configuration du RAG ; 0 pour un modèle local. Générique, quel que soit le fournisseur |
| 7 | Fiche de base de données | « page » = nom du champ (document 1) ; « un chunk par fiche » (document 2) | le rattachement accepte un chunk du même document dont la page est le nom du champ, **ou** dont le texte contient ce nom : un RAG qui fait un chunk par fiche est donc bien évalué. Le RAG d'exemple fait un chunk par champ |
| 8 | Taille du corpus d'exemple | `CLAUDE.md` : 12 documents, 30 questions ; document 1, configuration minimale : 10 documents par type, 50 questions, 20 pages OCR | **la configuration minimale du document 1 est atteinte** : 50 documents, 60 questions, 20 pages OCR. Un banc d'essai qui servira à d'autres doit être réaliste |
| 9 | Juge et RAG | « de préférence un autre modèle » | RAG : `gemma-4-e4b` ; juge et Ragas : `chat` (qwen3.5-4b), réflexion désactivée ; embeddings : `embed` (bge-m3) |
| 10 | Vérification du juge | accord d'au moins 90 % | appliqué tel quel ; le kit affiche aussi le kappa de Cohen, qui repère un juge qui dit presque toujours « juste » (Thakur et al., 2024) |
| 11 | Comparaison de deux versions | McNemar en configuration recommandée | fait : test exact, sans dépendance |
| 12 | Rattachement approché d'un texte | « il lui ressemble à 95 % » | ressemblance entre le passage et la partie du chunk qui lui ressemble le plus ; si le chunk est plus court que le passage, on compare les deux textes entiers (sinon un chunk qui ne porte que la moitié du passage passerait) |
| 13 | Une ligne fausse dans le fichier Excel | « rejet de la ligne, avec un message clair » | toutes les lignes fausses sont listées, et **rien n'est importé** tant qu'il en reste une : un corpus à moitié importé fausserait l'évaluation sans que personne ne s'en aperçoive |

## 2. Écarts avec les consignes de mise en œuvre (`CLAUDE.md`)

| Écart | Raison |
| --- | --- |
| Deux services indépendants, `service-rag/` et `service-evaluation/`, chacun avec son README, sa documentation, son `docker-compose.yml`, ses tests et son installation | le produit, c'est le service d'évaluation : il impose à tout RAG une porte de forme fixe. On lance d'abord le RAG, puis l'évaluation. Dans `service-evaluation/`, les guides et le code portent le même nom d'étape : 0a construction du corpus, 0b la porte du RAG, 1 à 4 l'évaluation de l'ingestion, de la recherche, de la réponse, de bout en bout (les niveaux 1 à 4 du document 3), et 5 les résultats ; un dossier de code Python ne pouvant pas commencer par un chiffre, ceux du kit s'appellent `etape_0a_corpus` … `etape_5_resultats`, et `appel_du_rag/` est le seul endroit qui parle à un RAG. Dans `service-rag/`, `pipeline/` est le RAG, et `porte_evaluation/` la seule partie écrite pour l'évaluation |
| Commandes `kit evaluer-ingestion`, `evaluer-recherche`, `evaluer-reponse`, `evaluer-bout-en-bout` au lieu de `kit niveau1` à `kit niveau4` | le nom dit ce qui est évalué ; les anciens noms marchent toujours (cachés dans l'aide) |
| Le RAG est évalué par **une porte à quatre portes, à une adresse web** (ingérer, montrer l'index, rechercher, répondre), et non par un connecteur Python | n'importe quel RAG, dans n'importe quel langage, se branche de la même façon. Le service d'évaluation envoie lui-même ses documents : il sait exactement ce que le RAG a reçu, ce qui compte pour évaluer l'ingestion. Le RAG les range à part de la production, et ne reçoit jamais les annotations |
| L'ontologie du domaine est à deux endroits : dans le RAG (`service-rag/config/ontologie.ttl`), pour extraire son graphe, et dans le service d'évaluation (`corpus_exemple/ontologie/`), avec ses règles SHACL, dont le kit lit le chemin dans `kit.yaml` (`graphe.formes`) | le contrat dit que « le projet fournit à côté `ontologie_formes.ttl` » : les règles appartiennent au projet, pas au RAG, qui ne doit pas fournir lui-même ce qui le contrôle |
| Le graphe entre dans l'index comme des éléments `noeud` (un par entité et par page, qui résume ses relations sur la page), et non comme un élément par relation | le contrat donne k éléments par recherche : un élément qui réunit les relations d'une entité en apporte plus au modèle pour la même place ; il garde la provenance d'une page, donc le filtre des droits et les citations marchent comme pour un chunk |
| Un passage coupé se cherche entre deux chunks de texte consécutifs, sans les éléments du graphe | un élément du graphe n'est pas un morceau du document : il casserait la suite des chunks |
| La version du RAG s'appelle `graphrag-<type_rag>-k<k>-<empreinte>` | on lit dans le nom si le graphe était allumé |
| Dans le banc d'essai, la relecture du métier (vérification du juge, justesse du graphe) est simulée par Claude, et ses notes sont versionnées dans `corpus_exemple/relecture_simulee/` | l'entreprise est fictive : il n'y a pas de métier réel. Les notes sont données sans voir la note du juge, avec leur raison, pour qu'on puisse les contester. Résultat : accord du juge 89 %, sous le seuil de 90 % (trois réponses que le juge dit « fausses » à tort) ; le juge n'est pas validé, et on ne retouche pas les notes pour le faire passer |
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
| Docling | conteneur `docling-serve-cpu`, port 5101 (`service-rag/docker-compose.yml`) |
| Python | 3.12, géré par uv ; deux projets indépendants, installés chacun dans son dossier (`service-evaluation/` : commande `kit` ; `service-rag/` : commande `rag`). Le RAG tourne aussi en conteneur, sa porte ouverte à http://127.0.0.1:8100 |
| Licences | uniquement MIT, Apache 2.0, BSD : reportlab, pypdfium2, Pillow, pypdf, rank-bm25, numpy, openai, jsonschema, rapidfuzz, jiwer, ragas, langfuse, typer, SQLAlchemy, openpyxl |
