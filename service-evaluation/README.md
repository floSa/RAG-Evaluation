# Service d'évaluation de RAG

Il évalue **n'importe quel RAG**, à partir d'un corpus annoté par le métier : des documents, des questions, la réponse attendue et l'endroit exact où elle se trouve. Il dit si le RAG lit bien les documents, s'il retrouve les bons passages, s'il répond juste, et s'il peut partir en production.

Il demande à chaque RAG une **porte de forme fixe**, à une adresse web : [la porte du RAG](documentation/0b_porte_du_rag.md). On lance donc **d'abord le RAG**, puis l'évaluation.

## Lancer le service

Il faut Docker, [uv](https://docs.astral.sh/uv/), et un point d'accès à des modèles de langage compatible OpenAI pour le juge (ici LLM-Service, sur http://127.0.0.1:8080). Depuis `service-evaluation/` :

```bash
cp .env.example .env
```

Mettre dans `.env` la clé du point d'accès (`KIT_LLM_CLE`). Puis démarrer Langfuse : la première commande ajoute ses secrets à `.env`, la seconde le démarre.

```bash
./initialiser.sh
```

```bash
docker compose up -d
```

Pour vérifier le juge, les embeddings et Langfuse :

```bash
uv run kit verifier-modeles
```

Langfuse est à http://127.0.0.1:3100 : l'adresse de connexion est `evaluation@valtera.example`, le mot de passe est `LANGFUSE_USER_PASSWORD` dans `.env`.

## Évaluer un RAG, en deux étapes

Le RAG doit être lancé, sa porte ouverte (pour le RAG d'exemple : [son README](../service-rag/README.md)).

**2a. Brancher le corpus annoté** ([guide 0a](documentation/0a_construction_du_corpus.md)) : le kit contrôle le fichier Excel du métier, le range, et crée le jeu de questions dans Langfuse.

```bash
uv run kit importer corpus_exemple/Corpus_evaluation_RAG.xlsx
```

**2b. Évaluer** ([guides 1 à 4](documentation/1_evaluation_ingestion.md)) : le kit appelle les quatre portes du RAG (il lui envoie les documents, lui pose les 60 questions, range ses réponses), puis enchaîne les quatre évaluations.

```bash
uv run kit evaluer
```

Le RAG est appelé à l'adresse de [`config/kit.yaml`](config/kit.yaml) (`rag.adresse`, http://127.0.0.1:8100) ; pour un autre RAG : `--rag http://…`. À la fin, la commande affiche le chemin de `rapport.html`, à ouvrir dans un navigateur ([guide 5](documentation/5_resultats_et_comparaison.md)).

## Ce qu'il y a dans le service

```
service-evaluation/
├── docker-compose.yml           Langfuse
├── config/                      le modèle juge et l'adresse du RAG (kit.yaml), les seuils du métier (seuils.json)
├── corpus_exemple/
│   ├── documents/               les 50 documents fictifs : c'est eux que le kit envoie au RAG
│   ├── Corpus_evaluation_RAG.xlsx   le fichier annoté par le métier : questions, réponses attendues, passages
│   └── ontologie/               l'ontologie du domaine et ses règles, pour contrôler le graphe d'un RAG
├── documentation/               les guides, dans l'ordre (ci-dessous), et reference/ : la méthode, le contrat, le prompt du juge
├── src/kit/
│   ├── etape_0a_corpus/         importer le corpus
│   ├── appel_du_rag/            appeler les quatre portes du RAG : le seul endroit qui parle à un RAG
│   ├── etape_1_evaluation_ingestion/ … etape_4_evaluation_bout_en_bout/
│   └── etape_5_resultats/       rapport, Langfuse, comparaison
└── tests/
```

## Les guides, dans l'ordre

| Guide | La question |
| --- | --- |
| [0a. Construction du corpus](documentation/0a_construction_du_corpus.md) | comment annoter le corpus, et l'importer |
| [0b. La porte du RAG](documentation/0b_porte_du_rag.md) | ce que chaque RAG doit fournir |
| [1. Évaluation de l'ingestion](documentation/1_evaluation_ingestion.md) | le passage est-il dans l'index ? |
| [2. Évaluation de la recherche](documentation/2_evaluation_recherche.md) | est-il retrouvé ? |
| [3. Évaluation de la réponse](documentation/3_evaluation_reponse.md) | la réponse est-elle juste ? (juge, relecture du métier) |
| [4. Évaluation de bout en bout](documentation/4_evaluation_bout_en_bout.md) | utile, sûr, rapide, pas cher ? la décision |
| [5. Résultats et comparaison](documentation/5_resultats_et_comparaison.md) | lire les résultats, comparer deux versions du RAG |

## Toutes les commandes

| Commande | Ce qu'elle fait | Guide |
| --- | --- | --- |
| `kit verifier-modeles` | teste le point d'accès, le juge, les embeddings et Langfuse | [3](documentation/3_evaluation_reponse.md) |
| `kit importer <fichier.xlsx>` | contrôle le fichier du métier, le range, crée le jeu de questions dans Langfuse | [0a](documentation/0a_construction_du_corpus.md) |
| `kit evaluer` | appelle les portes du RAG, puis enchaîne les évaluations 1 à 4 | [4](documentation/4_evaluation_bout_en_bout.md) |
| `kit appeler-rag` | appelle seulement les portes du RAG, et range ce qu'il rend | [0b](documentation/0b_porte_du_rag.md) |
| `kit verifier-contrat <dossier>` | dit précisément ce qui manque dans ce qu'un RAG a rendu | [0b](documentation/0b_porte_du_rag.md) |
| `kit evaluer-ingestion`, `evaluer-recherche`, `evaluer-reponse`, `evaluer-bout-en-bout` | une évaluation à la fois, sur des réponses déjà rangées | [1](documentation/1_evaluation_ingestion.md) à [4](documentation/4_evaluation_bout_en_bout.md) |
| `kit verifier-juge [--envoyer]` | fait noter 30 réponses par le métier, puis mesure l'accord avec le juge | [3](documentation/3_evaluation_reponse.md) |
| `kit verifier-graphe [--envoyer]` | fait juger 50 relations du graphe par le métier, puis mesure leur justesse | [1](documentation/1_evaluation_ingestion.md) |
| `kit comparer <résultats A> <résultats B>` | compare deux versions du RAG | [5](documentation/5_resultats_et_comparaison.md) |
| `kit init-base` | crée les tables de la base (fait aussi par `importer`) | [0a](documentation/0a_construction_du_corpus.md) |

Sans `--corpus`, le kit prend le dernier corpus importé ; sans `--rag`, les évaluations une à une prennent les dernières réponses rangées. Chaque commande a son aide : `uv run kit <commande> --help`.

## Arrêter

```bash
docker compose down
```

Les données de Langfuse (traces, scores, notes du métier) restent dans les volumes Docker.

## Tests

```bash
uv run pytest -q
```

Les tests utilisent des cas réels du corpus d'exemple. Un test vérifie que le kit n'importe rien d'un RAG.
