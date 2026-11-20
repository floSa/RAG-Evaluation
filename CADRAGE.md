# Étape 0 — Cadrage

Ce document fixe, avant toute ligne de code, l'arborescence, les commandes et les décisions prises sur les points ambigus des documents de référence. Les documents de `docs/` et `specs/` ne sont jamais modifiés ; quand ils laissent un choix ouvert, la décision est écrite ici.

## 1. Environnement de la machine

| Élément | État constaté le 2026-11-20 | Conséquence |
| --- | --- | --- |
| Modèles de langage | LLM-Service (`~/mes_projets/Projet-IA/LLM-Service`) : LiteLLM `llm-central`, `http://127.0.0.1:8080/v1` ; modèles `chat` (qwen3.5-4b, vision, réflexion), `embed` (bge-m3, 1024 dimensions), `rerank`, `gemma-4-e4b` (vision, réflexion) ; arrêté, à démarrer à la main | une clé par application : `kit` et `rag-demo`, écrites dans `.env` par `cle.sh` |
| Autre LiteLLM | `harness-litellm` (port 4100) : propre au Harness-Test-Bench | non utilisé |
| Carte graphique | RTX 4060 Ti, 16 Go | modèles locaux, coût nul |
| Docker | disponible ; port 3000 pris par `rag-open-webui` ; 8080 et 8081 pris par LLM-Service | Langfuse publié sur le port **3100** |
| Tesseract | absent (paquets `tesseract-ocr`, `tesseract-ocr-fra` disponibles, `sudo` requis) | à installer avant l'étape 4 |
| Python | 3.12.13 géré par `uv` | Python 3.12 (minimum du document ; règle de la machine) |

## 2. Arborescence détaillée

```
RAG-Evaluation/
├── CLAUDE.md                  consignes (référence)
├── CADRAGE.md                 ce document
├── README.md                  mode d'emploi (réécrit à l'étape 10)
├── pyproject.toml, uv.lock    un seul projet uv, deux paquets, deux commandes
├── .env.example               adresses et clés attendues (jamais de vraie clé)
├── docs/                      documents de référence (jamais modifiés)
├── specs/
│   ├── CONTRAT.md, JUGE.md    références
│   └── schemas/               un schéma JSON par fichier du contrat (étape 3)
├── config/
│   ├── kit.yaml               point d'accès, modèles du juge et des embeddings, seuils de ressemblance, chemins
│   └── seuils.json            seuil, sens, bloquant pour chaque score (document 3, section 9)
├── infra/
│   ├── docker-compose.yml     Langfuse v3 auto-hébergé (web, worker, PostgreSQL, ClickHouse, Redis, MinIO)
│   └── .env.example
├── corpus_exemple/
│   ├── fabrication/           scripts qui fabriquent le corpus fictif (contenus, PDF, scan bruité, fiche)
│   ├── sources/               les 12 documents PDF
│   ├── Corpus_evaluation_RAG.xlsx   le fichier du métier, rempli
│   └── ontologie/             ontologie et règles SHACL (étape 9)
├── kit/
│   ├── cli.py                 la commande `kit`
│   ├── config.py              lecture de kit.yaml, seuils.json, .env
│   ├── base.py                tables SQLAlchemy (document 1, section 5)
│   ├── import_corpus.py       Excel → contrôles → base → corpus/<version>/ → jeu Langfuse
│   ├── contrat.py             lecture et validation des fichiers du contrat (schémas JSON)
│   ├── lanceur.py             appelle un connecteur Python et écrit recherches.jsonl, reponses.jsonl
│   ├── niveau1.py             rattachement, liens_index, scores n1_*
│   ├── niveau2.py             scores n2_*
│   ├── niveau3.py             scores n3_* (script, juge, Ragas), croisement recherche × réponse
│   ├── juge.py                prompt de JUGE.md, sortie JSON, vérification du juge
│   ├── niveau4.py             score pondéré, temps, coût, marges, décision
│   ├── publication.py         écriture base, resultats/, Langfuse
│   └── rapport.py             rapport.html et comparaison de deux évaluations
├── rag_demo/
│   ├── config.yaml            point d'accès, modèles, k, découpage, droits
│   ├── cli.py                 la commande `rag-demo`
│   ├── extraction.py          PDF natif (pdfplumber), OCR (pytesseract), tableaux, images (vision)
│   ├── decoupage.py           par section, chemin de titres, métadonnées du contrat
│   ├── index.py               embeddings (numpy) + BM25, filtre des droits
│   ├── generation.py          réponse citée, abstention
│   ├── connecteur.py          les six méthodes du contrat
│   └── graphe.py              variante graphe (étape 9)
├── tests/
│   ├── kit/  rag_demo/
│   └── test_separation.py     vérifie que kit/ et rag_demo/ ne s'importent pas l'un l'autre
└── sorties/                   non versionné
    ├── base.sqlite
    ├── corpus/<version_corpus>/
    ├── sorties_rag/<version_rag>/
    └── resultats/<evaluation_id>/
```

## 3. Les commandes

| Commande | Étape | Ce qu'elle fait |
| --- | --- | --- |
| `docker compose -f infra/docker-compose.yml up -d` | 1 | démarre Langfuse (http://127.0.0.1:3100) |
| `kit init-base` | 1 | crée les tables de la base relationnelle |
| `uv run python corpus_exemple/fabrication/fabriquer.py` | 2 | fabrique les PDF et remplit le fichier Excel du corpus d'exemple |
| `kit importer <fichier.xlsx>` | 3 | contrôle, charge en base, exporte `corpus/<version>/`, crée le jeu Langfuse |
| `kit verifier-contrat <dossier>` | 3 | valide les fichiers d'un RAG contre `specs/schemas/` |
| `rag-demo indexer` | 4 | extraction, découpage, embeddings, index |
| `rag-demo exporter` | 4 | écrit rag.json, chunks.jsonl, pages_extraites.jsonl (et graphe.ttl en variante graphe) |
| `rag-demo repondre <questions.jsonl>` | 4 | écrit recherches.jsonl et reponses.jsonl |
| `kit lancer --connecteur rag_demo.connecteur:Connecteur` | 4 | même résultat par le connecteur ; le kit charge l'objet par son nom, sans import écrit dans son code |
| `kit niveau1 <sorties_rag>` … `kit niveau4 <sorties_rag>` | 5 à 8 | un niveau à la fois |
| `kit verifier-juge` | 7 | taux d'accord juge / métier à partir des notes de la file `verification-juge` |
| `kit evaluer <sorties_rag>` | 8 | enchaîne les niveaux 1 à 4 |
| `kit comparer <evaluation_a> <evaluation_b>` | 8 | écarts de scores, questions gagnées et perdues |

## 4. Choix techniques complémentaires

| Sujet | Choix | Licence |
| --- | --- | --- |
| Fabrication des PDF natifs, du schéma | reportlab | BSD |
| Rendu des pages scannées, bruit | pypdfium2, Pillow | Apache 2.0 / BSD, HPND |
| Lecture des PDF dans le RAG | pdfplumber (texte, tableaux) ; pypdfium2 (images de page pour l'OCR et la vision) | MIT ; Apache 2.0 |
| BM25 | rank-bm25 | Apache 2.0 |
| Base vectorielle du RAG de démonstration | tableau numpy en mémoire, enregistré sur disque ; filtre des droits appliqué avant le classement | BSD |
| Schémas JSON | jsonschema | MIT |
| Ligne de commande | typer | MIT |
| Client des modèles | openai (point d'accès compatible) | Apache 2.0 |
| Paquets | un seul `pyproject.toml`, deux paquets (`kit`, `rag_demo`), deux commandes ; séparation vérifiée par un test | — |

## 5. Décisions sur les points ambigus

| # | Point | Ce que disent les documents | Décision proposée |
| --- | --- | --- | --- |
| 1 | Identifiant d'un passage | « numéro de ligne », « stable d'une version à l'autre tant que la ligne ne change pas » (CONTRAT §2) : une ligne insérée plus haut décale les numéros | à la première importation, `passage_id` = numéro de la ligne Excel ; ensuite, une ligne identique (question, référence, page, type d'élément, passage, répond) garde son identifiant, une ligne nouvelle ou modifiée reçoit le plus grand identifiant + 1 |
| 2 | Réponse « non fidèle » dans `n3_erreurs_graves` | « réponses fausses, ou non fidèles, à une question de gravité forte » ; aucun seuil par question | non fidèle = fidélité Ragas de la réponse < 0,5 ; réglable dans `kit.yaml` |
| 3 | Score pondéré : questions sans réponse | « somme des poids des réponses justes » ; le juge ne note que les questions `oui` | question `non` ou `non_accessible` : juste si le RAG s'abstient, fausse sinon ; question `oui` où le RAG s'abstient : fausse |
| 4 | Marge d'erreur des scores qui ne sont pas des proportions | formule ± 1,96 × √(p(1−p)/n), écrite pour une proportion | appliquée telle quelle aux scores entre 0 et 1 (MRR, fidélité, exactitude) ; `null` pour les nombres (fuite, erreurs graves), les temps et les coûts |
| 5 | Questions réservées à la décision | « l'équipe technique n'en voit que les scores globaux » | les scores de réglage (rapport, CSV, Langfuse) portent sur les questions non réservées ; un bloc `decision` de `scores.json` donne les scores globaux des questions réservées ; leur détail question par question reste dans la base seulement, sans score par trace dans Langfuse |
| 6 | Coût en euros | `cout` en euros ; LiteLLM calcule en dollars, et 0 pour un modèle local | coût lu dans la réponse de LiteLLM × taux dollar → euro de `rag_demo/config.yaml` ; 0 avec les modèles locaux |
| 7 | Modèle Excel | contient des lignes d'exemple et des sources réelles (« Base de données EDF », « Caméléon ») | la copie de `corpus_exemple/` est vidée de ses exemples ; feuille Listes complétée avec des sources et profils fictifs |
| 8 | Fiche de base de données | pas de type d'élément dédié | passage de type `texte`, nom du champ dans « Page » (comme l'exemple du modèle) |
| 9 | Taille du corpus d'exemple | CLAUDE.md : 12 documents, 30 questions, 3 pages OCR ; configuration minimale : 10 documents par type, 50 questions, 20 pages OCR | on suit CLAUDE.md ; le tableau de bord montrera « À compléter » sur ces lignes et l'import émettra l'avertissement prévu (sans rejet) |
| 10 | Juge différent du RAG | « de préférence un autre modèle que celui du RAG » | génération : `chat` (qwen3.5-4b) ; juge et Ragas : `gemma-4-e4b` ; réflexion désactivée pour les deux |

## 6. Risques repérés

| Risque | Parade |
| --- | --- |
| Des modèles de 4 milliards de paramètres comme juge : sorties JSON parfois invalides, notes Ragas instables | sortie redemandée une fois (JUGE.md) ; vérification du juge sur 30 réponses ; activer un modèle en ligne dans LLM-Service si l'accord est sous 90 % |
| Files de relecture de Langfuse par l'API | vérifié à l'étape 1 sur la version installée ; sinon, création manuelle documentée |
| Tesseract absent | installation par l'utilisateur avant l'étape 4 |
