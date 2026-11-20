# Décisions et écarts

Les documents de référence ([`docs/`](docs/README.md), le [contrat](corpus/contrat/CONTRAT.md), le [juge](evaluation/juge/JUGE.md)) font foi et ne sont jamais modifiés. Quand ils laissent un choix ouvert, ou quand la mise en œuvre s'en écarte, la décision est écrite ici, avec sa raison.

## 1. Décisions sur les points que la méthode laisse ouverts

| # | Point | Ce que disent les documents | Décision |
| --- | --- | --- | --- |
| 1 | Identifiant d'un passage | « numéro de ligne », « stable d'une version à l'autre tant que la ligne ne change pas » ; or une ligne insérée plus haut décale les numéros | premier import : `passage_id` = numéro de la ligne Excel. Ensuite, une ligne identique (question, document, page, type, passage, répond) garde son identifiant ; une ligne nouvelle ou modifiée reçoit un identifiant jamais utilisé |
| 2 | Réponse « non fidèle » dans les erreurs graves | aucun seuil par question | non fidèle = **au moins une affirmation non appuyée** (fidélité Ragas < 1,0), réglable (`seuil_non_fidele` dans `kit.yaml`). C'est la règle de Lynx, RAGTruth, Azure Groundedness Pro et DeepEval en mode strict ; le seuil de 0,5 des outils est trop laxiste pour une question à risque. Chaque cas est relu par le métier |
| 3 | Score pondéré : questions sans réponse | « somme des poids des réponses justes » | question sans réponse ou interdite : juste si le RAG s'abstient, fausse sinon ; question avec réponse où le RAG s'abstient : fausse. Règle de CRAG (2024) et SQuAD 2.0, sans la pénalité négative de CRAG |
| 4 | Marge d'erreur | formule écrite pour une proportion | appliquée aux scores entre 0 et 1 (pour une moyenne de valeurs entre 0 et 1, la variance est au plus p(1−p) : la marge est prudente) ; pas de marge pour les nombres, temps et coûts. La formule ne sait pas estimer l'incertitude à 0 % et 100 % : l'intervalle de Wilson ou le rééchantillonnage relèvent de la configuration recommandée |
| 5 | Questions réservées à la décision | « l'équipe technique n'en voit que les scores globaux » | le rapport, le CSV, Langfuse et les scores de `scores.json` portent sur les questions non réservées. Le bloc `decision` donne les scores des questions réservées, sans détail. Les critères bloquants se jugent sur toutes les questions. Le détail des réservées reste dans la base |
| 6 | Coût | en euros | prix au million de tokens d'entrée et de sortie dans la configuration du RAG ; 0 pour un modèle local. Générique, quel que soit le fournisseur |
| 7 | Fiche de base de données | « page » = nom du champ (document 1) ; « un chunk par fiche » (document 2) | le rattachement accepte un chunk du même document dont la page est le nom du champ, **ou** dont le texte contient ce nom : un RAG qui fait un chunk par fiche est donc bien évalué. Le RAG de démonstration fait un chunk par champ |
| 8 | Taille du corpus d'exemple | `CLAUDE.md` : 12 documents, 30 questions ; document 1, configuration minimale : 10 documents par type, 50 questions, 20 pages OCR | **la configuration minimale du document 1 est atteinte** : 50 documents, 60 questions, 20 pages OCR. Un banc d'essai qui servira à d'autres doit être réaliste |
| 9 | Juge et RAG | « de préférence un autre modèle » | RAG : `gemma-4-e4b` ; juge et Ragas : `chat` (qwen3.5-4b), réflexion désactivée ; embeddings : `embed` (bge-m3) |
| 10 | Vérification du juge | accord d'au moins 90 % | appliqué tel quel ; le kit affiche aussi le kappa de Cohen, qui repère un juge qui dit presque toujours « juste » (Thakur et al., 2024) |
| 11 | Comparaison de deux versions | McNemar en configuration recommandée | fait : test exact, sans dépendance |
| 12 | Rattachement approché d'un texte | « il lui ressemble à 95 % » | ressemblance entre le passage et la partie du chunk qui lui ressemble le plus ; si le chunk est plus court que le passage, on compare les deux textes entiers (sinon un chunk qui ne porte que la moitié du passage passerait) |
| 13 | Une ligne fausse dans le fichier Excel | « rejet de la ligne, avec un message clair » | toutes les lignes fausses sont listées, et **rien n'est importé** tant qu'il en reste une : un corpus à moitié importé fausserait l'évaluation sans que personne ne s'en aperçoive |

## 2. Écarts avec les consignes de mise en œuvre (`CLAUDE.md`)

| Écart | Raison |
| --- | --- |
| Trois dossiers `corpus/`, `rag/`, `evaluation/` au lieu de `kit/`, `rag_demo/`, `config/`, `specs/` à la racine | lisibilité : chaque partie a son dossier et son guide. Le contrat est rangé avec le corpus (`corpus/contrat/`) ; le prompt du juge avec l'évaluation (`evaluation/juge/`) |
| Docling (conteneur) au lieu de `pytesseract` pour l'OCR du RAG de démonstration | rien à installer sur la machine ; c'est l'outil cité par le document 2. Le kit n'en dépend pas : il mesure l'OCR de n'importe quel RAG avec jiwer |
| Pas de modèle de vision dans le RAG de démonstration : une figure est connue par sa légende | le RAG est un prétexte ; le kit montre la perte (question Q-034) |
| Langfuse v4 au lieu de v3 | v3 n'est plus la version courante ; le client Python actuel exige v4 |
| Expérience Langfuse créée en rejouant les réponses du RAG (`run_experiment`), au lieu de relier les traces du RAG au jeu de données | Langfuse v4 ne permet plus de relier une trace existante à un jeu de données. Chaque ligne de l'expérience garde l'identifiant de la trace du RAG (`trace_rag`) |
| La table `resultats` a quatre colonnes de plus (objet évalué, axes de ventilation, poids, réservée) ; une table `corpus` en plus | recalculer tous les scores et leurs ventilations depuis la base, niveau par niveau |
| Fichiers en plus dans `resultats/` : `passages_non_rattaches.jsonl`, `croisement.jsonl`, `relecture.jsonl`, `langfuse.json` | la liste des passages non rattachés est demandée à l'étape 5 ; le croisement à l'étape 7 |
| `openai` < 3 | exigé par Ragas 0.4 (par sa dépendance `instructor`) |

## 3. Ce qui n'est pas fait (configuration recommandée, ou étape suivante)

| Point | État |
| --- | --- |
| Variante graphe du RAG (étape 9) et ses scores (`n1_graphe_violations`, `n1_graphe_justesse`) | non commencée |
| `n2_ndcg_k` (ranx), `n3_second_avis` (FactualCorrectness), marge par rééchantillonnage | configuration recommandée ; non faits |
| Vérification réelle du juge par le métier | le mécanisme est prêt (`kit verifier-juge`) ; il faut que le métier note les 30 réponses dans Langfuse |

## 4. Environnement du bac à sable

| Élément | Choix |
| --- | --- |
| Modèles | LLM-Service (LiteLLM local, `http://127.0.0.1:8080/v1`) ; une clé pour le kit, une pour le RAG |
| Langfuse | auto-hébergé, v4, port 3100 (`infra/`) |
| Docling | conteneur `docling-serve-cpu`, port 5101 (`infra/`) |
| Python | 3.12, géré par uv ; un seul projet, deux paquets (`kit`, `rag_demo`), deux commandes |
| Licences | uniquement MIT, Apache 2.0, BSD : reportlab, pypdfium2, Pillow, pypdf, rank-bm25, numpy, openai, jsonschema, rapidfuzz, jiwer, ragas, langfuse, typer, SQLAlchemy, openpyxl |
