# Service d'évaluation de RAG

Ce dossier est le **service d'évaluation, vierge**. On le prend tel quel pour son propre projet : on y met son corpus, on le branche sur son RAG, et il dit si ce RAG peut partir en production.

Pour voir ce qu'il produit une fois rempli et lancé, sans rien installer : [`service-evaluation-exemple/`](../service-evaluation-exemple/README.md).

## Ce qu'il fait

Un **RAG** répond à des questions en s'appuyant sur des documents : il les découpe en morceaux de texte, retrouve les morceaux utiles à une question, puis fait écrire la réponse par un modèle de langage.

Le service évalue un RAG à partir d'un **corpus annoté** : des documents, et un fichier Excel où le métier a écrit des questions, leur bonne réponse, et l'endroit exact des documents où elle se trouve.

Il fait deux choses :

- **Évaluer une configuration.** Une configuration, c'est le RAG avec tous ses réglages fixés : par exemple le nombre de morceaux que la recherche ramène pour chaque question, le modèle qui écrit la réponse. Le service pose toutes les questions au RAG, note ce qu'il fait à chaque étape, et répond : *cette configuration peut-elle partir en production ?*
- **Comparer deux configurations** déjà évaluées, par exemple 5 ou 3 morceaux ramenés : *laquelle fait mieux, et l'écart est-il réel ou dû au hasard ?*

Chaque évaluation et chaque comparaison produit un rapport, `RAPPORT.md`, lisible directement sur GitHub.

## Ce qu'il y a dans ce dossier

| Dossier | À quoi il sert | Ce que vous en faites |
| --- | --- | --- |
| [`config/`](config/) | les réglages du service : le modèle juge, l'adresse du RAG, et les seuils que le métier fixe pour décider | **à régler** une fois pour le projet |
| [`corpus_annote/`](corpus_annote/) | le corpus documentaire que le RAG doit lire, et le fichier Excel que le métier remplit | **à remplir** |
| [`endpoints_a_copier/`](endpoints_a_copier/) | le code des quatre endpoints que votre RAG doit ouvrir pour être évalué | **à copier** dans votre RAG |
| [`resultats/`](resultats/) | tout ce que le service produit : le corpus contrôlé, les réponses du RAG, les évaluations, les comparaisons | **se remplit seul** ; on y lit les `RAPPORT.md` |
| [`documentation/`](documentation/) | les guides, dans l'ordre, et la méthode | **à lire** |
| [`src/`](src/) et [`tests/`](tests/) | le code du service, et ses tests | à ne pas toucher |

Les fichiers à la racine servent à l'installer : `docker-compose.yml` démarre Langfuse, l'outil web où le métier relit les réponses ; `initialiser.sh` prépare ses mots de passe ; `pyproject.toml` et `uv.lock` listent les bibliothèques Python ; `.env.example` montre les clés à fournir.

## Le faire tourner, dans l'ordre

Pas à pas détaillé, avec votre propre RAG : [intégrer votre RAG](documentation/integrer_votre_rag.md).

**1. Installer.** Il faut Docker, [uv](https://docs.astral.sh/uv/), et un accès à des modèles de langage par une API compatible OpenAI. Depuis ce dossier :

```bash
cp .env.example .env
```

Mettre dans `.env` la clé de l'API des modèles (`KIT_LLM_CLE`), puis démarrer Langfuse :

```bash
./initialiser.sh
```

```bash
docker compose up -d
```

Langfuse est à http://127.0.0.1:3100. L'identifiant est `evaluation@valtera.example`, et le mot de passe est la ligne `LANGFUSE_USER_PASSWORD` de `.env`. Pour vérifier que le juge et Langfuse répondent :

```bash
uv run kit verifier-modeles
```

**2. Régler** [`config/`](config/) : le nom du projet, l'adresse de votre RAG, et les seuils, fixés avec le métier avant toute évaluation.

**3. Remplir** [`corpus_annote/`](corpus_annote/) : vos documents dans `corpus_documentaire/`, et le fichier Excel, rempli par le métier ([guide 0a](documentation/0a_construction_du_corpus.md)).

**4. Importer le corpus.** Le service contrôle le fichier Excel et dit précisément ce qui ne va pas.

```bash
uv run kit importer corpus_annote/Corpus_evaluation_RAG.xlsx
```

**5. Brancher le RAG.** Votre RAG ouvre les quatre endpoints décrits dans le [guide 0b](documentation/0b_endpoints_du_rag.md), à partir du code de [`endpoints_a_copier/`](endpoints_a_copier/).

**6. Évaluer une configuration.** Le service envoie les documents au RAG, lui pose toutes les questions, puis enchaîne les quatre évaluations.

```bash
uv run kit evaluer
```

**7. Lire le rapport.** La commande affiche à la fin le chemin du `RAPPORT.md`, dans `resultats/evaluations/`. Comment le lire : [guide 5](documentation/5_resultats_et_comparaison.md).

**8. Comparer.** Après un changement de réglage, on évalue la nouvelle configuration, puis on la compare à l'ancienne :

```bash
uv run kit comparer resultats/evaluations/<configuration A> resultats/evaluations/<configuration B>
```

### Essayer avec le corpus d'exemple

Pour essayer le service sans corpus à soi, on lui donne celui de l'exemple, puis on suit les étapes 4 à 8. Le RAG d'exemple doit être lancé ([son README](../service-rag-exemple/README.md)).

```bash
cp -r ../service-evaluation-exemple/corpus_annote/corpus_documentaire ../service-evaluation-exemple/corpus_annote/ontologie corpus_annote/
```

```bash
uv run kit importer ../service-evaluation-exemple/corpus_annote/Corpus_evaluation_RAG.xlsx
```

```bash
uv run kit evaluer
```

Vos chiffres peuvent différer de quelques points de ceux de l'exemple : le modèle qui écrit les réponses ne répond pas toujours pareil.

## Les guides, dans l'ordre

| Guide | Ce qu'il explique |
| --- | --- |
| [Intégrer votre RAG](documentation/integrer_votre_rag.md) | par où commencer pour votre projet, du corpus à la décision |
| [0a. Construction du corpus](documentation/0a_construction_du_corpus.md) | comment le métier annote le corpus, et comment l'importer |
| [0b. Les endpoints du RAG](documentation/0b_endpoints_du_rag.md) | ce que votre RAG doit ouvrir pour être évalué |
| [1. Évaluation de l'ingestion](documentation/1_evaluation_ingestion.md) | rien ne s'est-il perdu quand le RAG a rangé les documents dans sa base ? |
| [2. Évaluation de la recherche](documentation/2_evaluation_recherche.md) | la recherche ramène-t-elle les morceaux qui contiennent la réponse ? |
| [3. Évaluation de la réponse](documentation/3_evaluation_reponse.md) | la réponse est-elle juste, fondée sur les documents ? |
| [4. Évaluation de bout en bout](documentation/4_evaluation_bout_en_bout.md) | le RAG est-il bon sur ce qui compte, assez rapide, pas trop cher ? Et la décision |
| [5. Résultats et comparaison](documentation/5_resultats_et_comparaison.md) | lire un rapport, comparer deux configurations |

## Toutes les commandes

À lancer depuis ce dossier. Chaque commande a son aide : `uv run kit <commande> --help`.

| Commande | Ce qu'elle fait | Guide |
| --- | --- | --- |
| `kit verifier-modeles` | vérifie que le juge, les embeddings et Langfuse répondent | [3](documentation/3_evaluation_reponse.md) |
| `kit importer <fichier.xlsx>` | contrôle le fichier du métier, le range dans `resultats/corpus/`, crée le jeu de questions dans Langfuse | [0a](documentation/0a_construction_du_corpus.md) |
| `kit evaluer` | appelle les endpoints du RAG, puis enchaîne les évaluations 1 à 4 | [4](documentation/4_evaluation_bout_en_bout.md) |
| `kit appeler-rag` | appelle seulement les endpoints du RAG, et range ses réponses dans `resultats/reponses_du_rag/` | [0b](documentation/0b_endpoints_du_rag.md) |
| `kit verifier-contrat <dossier>` | dit précisément ce qui manque dans ce qu'un RAG a rendu | [0b](documentation/0b_endpoints_du_rag.md) |
| `kit evaluer-ingestion`, `evaluer-recherche`, `evaluer-reponse`, `evaluer-bout-en-bout` | une évaluation à la fois, sur des réponses déjà rangées | [1](documentation/1_evaluation_ingestion.md) à [4](documentation/4_evaluation_bout_en_bout.md) |
| `kit verifier-juge [--envoyer]` | fait noter 30 réponses par le métier, puis mesure son accord avec le juge | [3](documentation/3_evaluation_reponse.md) |
| `kit verifier-graphe [--envoyer]` | fait juger 50 relations du graphe par le métier, puis mesure leur justesse | [1](documentation/1_evaluation_ingestion.md) |
| `kit comparer <évaluation A> <évaluation B>` | compare deux configurations déjà évaluées ; écrit son rapport dans `resultats/comparaisons_de_configurations/` | [5](documentation/5_resultats_et_comparaison.md) |
| `kit init-base` | crée la base de données du service (fait aussi par `importer`) | [0a](documentation/0a_construction_du_corpus.md) |

Trois options valent pour toutes les commandes :

| Option | Ce qu'elle désigne | Sans elle |
| --- | --- | --- |
| `--corpus` | un corpus importé : `resultats/corpus/<version>/` | le dernier importé |
| `--rag` | le RAG évalué : l'adresse de ses endpoints (`http://…`), ou un dossier `resultats/reponses_du_rag/<version>/` déjà rempli | `evaluer` et `appeler-rag` : l'adresse de `config/kit.yaml` ; les autres : le dossier le plus récent |
| `--dossier`, avant la commande | un autre dossier de service, par exemple `kit --dossier ../service-evaluation-exemple …` | ce dossier-ci |

## Arrêter

```bash
docker compose down
```

Les données de Langfuse (traces, scores, notes du métier) restent dans les volumes Docker.

## Tests

```bash
uv run pytest -q
```

Les tests utilisent des cas réels du corpus d'exemple. Un test vérifie que le service n'importe rien du code d'un RAG.
