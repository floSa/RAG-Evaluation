# Service d'évaluation de RAG

Il évalue **n'importe quel RAG**, à partir d'un corpus annoté par le métier : des documents, des questions, la réponse attendue et l'endroit exact où elle se trouve. Il dit si le RAG lit bien les documents, s'il retrouve les bons passages, s'il répond juste, et s'il peut partir en production.

Il demande à chaque RAG **quatre portes de forme fixe**, à une adresse web : [la porte du RAG](documentation/0b_porte_du_rag.md). On lance donc **d'abord le RAG**, puis l'évaluation.

## Lancer le service

Il faut Docker, [uv](https://docs.astral.sh/uv/), et un point d'accès à des modèles de langage compatible OpenAI pour le juge (ici LLM-Service, sur http://127.0.0.1:8080 ; pour un autre fournisseur, changer `modeles` dans [`config/kit.yaml`](config/kit.yaml)). Depuis `service-evaluation/` :

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

Le RAG doit être lancé, ses portes ouvertes (pour le RAG d'exemple : [son README](../service-rag/README.md)).

**Temps 2a. Brancher le corpus annoté** ([guide 0a](documentation/0a_construction_du_corpus.md)) : le kit contrôle le fichier Excel du métier, le range, et crée le jeu de questions dans Langfuse.

```bash
uv run kit importer corpus_exemple/Corpus_evaluation_RAG.xlsx
```

**Temps 2b. Évaluer** ([guides 1 à 4](documentation/1_evaluation_ingestion.md)) : le kit appelle les quatre portes du RAG (il lui envoie les documents, lui pose les 60 questions, range ses réponses), puis enchaîne les quatre évaluations.

```bash
uv run kit evaluer
```

Le RAG est appelé à l'adresse de [`config/kit.yaml`](config/kit.yaml) (`rag.adresse`, http://127.0.0.1:8100) ; pour un autre RAG : `--rag http://…` (voir [les options](#les-options---corpus-et---rag)). À la fin, la commande affiche le chemin de `rapport.html`, à ouvrir dans un navigateur ([guide 5](documentation/5_resultats_et_comparaison.md)).

## Ce qu'il y a dans le service

```
service-evaluation/
├── docker-compose.yml           Langfuse
├── initialiser.sh               écrit les secrets de Langfuse dans .env
├── config/                      le modèle juge et l'adresse du RAG (kit.yaml), les seuils du métier (seuils.json)
├── corpus_exemple/
│   ├── documents/               les 50 documents fictifs : c'est eux que le kit envoie au RAG
│   ├── Corpus_evaluation_RAG.xlsx   le fichier annoté par le métier : questions, réponses attendues, passages
│   ├── questions_pour_relecture.md  les 60 questions sur une page (générée depuis le fichier Excel)
│   ├── ontologie/               l'ontologie du domaine et ses règles, pour contrôler le graphe d'un RAG
│   ├── relecture_simulee/       les notes du métier, jouées par Claude (banc d'essai seulement)
│   └── fabrication/             le script qui a fabriqué les 50 documents (rarement utile)
├── documentation/               les guides, dans l'ordre (ci-dessous), et reference/ : la méthode, le contrat, le prompt du juge.
│                                reference/schemas/ et reference/prompt_du_juge.md sont lus par le kit : les modifier change l'évaluation
├── src/kit/
│   ├── etape_0a_corpus/         importer le corpus
│   ├── appel_du_rag/            appeler les quatre portes du RAG : le seul endroit qui parle à un RAG
│   ├── contrat.py               lire et vérifier les fichiers échangés (corpus, réponses du RAG)
│   ├── etape_1_evaluation_ingestion/ … etape_4_evaluation_bout_en_bout/
│   └── etape_5_resultats/       rapport, Langfuse, comparaison
└── tests/
```

## Les guides, dans l'ordre

Les quatre évaluations sont les niveaux 1 à 4 de la méthode (document 3) : d'où les préfixes `n1_` à `n4_` des scores. Une **évaluation**, au sens d'un dossier de résultats (`sorties/resultats/<…>/`), c'est un corpus évalué avec une version du RAG.

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
| `python corpus_exemple/relecture_simulee/publier.py` | banc d'essai seulement : inscrit dans Langfuse les notes du métier, jouées par Claude | [1](documentation/1_evaluation_ingestion.md), [3](documentation/3_evaluation_reponse.md) |
| `kit comparer <résultats A> <résultats B>` | compare deux versions du RAG | [5](documentation/5_resultats_et_comparaison.md) |
| `kit init-base` | crée les tables de la base (fait aussi par `importer`) | [0a](documentation/0a_construction_du_corpus.md) |

### Les options `--corpus` et `--rag`

| Option | Ce qu'elle désigne | Sans elle |
| --- | --- | --- |
| `--corpus` | un corpus importé : `sorties/corpus/<version>/` | le dernier importé |
| `--rag` | le RAG évalué : soit l'adresse de ses portes (`http://…`), soit un dossier `sorties/sorties_rag/<version du RAG>/` déjà rempli | `evaluer` et `appeler-rag` : l'adresse de `config/kit.yaml` ; les évaluations une à une : le dossier le plus récent |

Le kit affiche toujours le corpus et le RAG qu'il a choisis. Chaque commande a son aide : `uv run kit <commande> --help`.

## Les documents de la méthode

Les textes et le code citent la méthode par numéro :

| Nom dans les textes | Fichier |
| --- | --- |
| document 1 : le corpus annoté | [`documentation/reference/methode_corpus_annote.md`](documentation/reference/methode_corpus_annote.md) |
| document 2 : les techniques d'un RAG | [`../service-rag/documentation/reference/techniques_rag.md`](../service-rag/documentation/reference/techniques_rag.md) |
| document 3 : l'évaluation | [`documentation/reference/methode_evaluation.md`](documentation/reference/methode_evaluation.md) |

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
