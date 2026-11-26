# Service d'évaluation de RAG

Ce dossier est le **service d'évaluation, vierge**. On le prend tel quel pour son propre projet : on y met son corpus, on le branche sur son RAG, et il en donne les scores : pour choisir la meilleure configuration, mesurer une amélioration, et éclairer la décision de mise en production, que prend le métier.

**Commencez par le [fil conducteur](FIL_CONDUCTEUR.md)** : il explique ce qu'on fait et pourquoi, dans l'ordre, et renvoie vers le guide de chaque étape.

Pour voir ce qu'il produit une fois rempli et lancé, sans rien installer : [`service-evaluation-exemple/`](../service-evaluation-exemple/README.md).

## Ce qu'il fait

Un **RAG** répond à des questions en s'appuyant sur des documents : il les découpe en morceaux de texte, retrouve les morceaux utiles à une question, puis fait écrire la réponse par un modèle de langage.

Le service évalue un RAG à partir d'un **corpus annoté** : des documents, et un fichier Excel où le métier a écrit des questions, leur bonne réponse, et l'endroit exact des documents où elle se trouve.

Il fait deux choses :

- **Évaluer une configuration.** Une configuration, c'est le RAG avec tous ses réglages fixés : par exemple le nombre de morceaux que la recherche ramène pour chaque question, le modèle qui écrit la réponse. Le service pose toutes les questions au RAG, note ce qu'il fait à chaque étape, et donne les scores, chacun en une phrase que le métier comprend. C'est le métier qui décide, à leur lecture, si la configuration peut partir en production.
- **Comparer deux configurations** déjà évaluées, par exemple 5 ou 3 morceaux ramenés : *laquelle fait mieux, et l'écart est-il réel ou dû au hasard ?*

Chaque évaluation et chaque comparaison produit un rapport, `RAPPORT.md`, lisible directement sur GitHub.

## Ce qu'il y a dans ce dossier

| Dossier | À quoi il sert | Ce que vous en faites |
| --- | --- | --- |
| [`config/`](config/) | les réglages du service : le modèle juge et l'adresse du RAG | **à régler** une fois pour le projet |
| [`corpus_annote/`](corpus_annote/) | le corpus documentaire que le RAG doit lire, et le fichier Excel que le métier remplit | **à remplir** |
| [`endpoints_a_copier/`](endpoints_a_copier/) | le code des quatre endpoints que votre RAG doit ouvrir pour être évalué | **à copier** dans votre RAG |
| [`resultats/`](resultats/) | tout ce que le service produit : le corpus contrôlé, les réponses du RAG, les évaluations, les comparaisons | **se remplit seul** ; on y lit les `RAPPORT.md` |
| [`documentation/`](documentation/) | les guides, dans l'ordre, et la méthode | **à lire** |
| [`src/`](src/) et [`tests/`](tests/) | le code du service, et ses tests | à ne pas toucher |

À la racine : le [fil conducteur](FIL_CONDUCTEUR.md), puis les fichiers qui servent à installer le service : `docker-compose.yml` démarre Langfuse, l'outil web où le métier relit les réponses ; `initialiser.sh` prépare ses mots de passe ; `pyproject.toml` et `uv.lock` listent les bibliothèques Python ; `.env.example` montre les clés à fournir.

## Installer le service

C'est l'étape 0 du [fil conducteur](FIL_CONDUCTEUR.md#0-installer-le-service-dévaluation). Toutes les commandes se lancent depuis ce dossier.

Il faut Docker, [uv](https://docs.astral.sh/uv/), et un accès à des modèles de langage par une API compatible OpenAI. L'installation met en place :

| Ce qui s'installe | À quoi ça sert | Comment |
| --- | --- | --- |
| la commande `kit` | le service lui-même : importer le corpus, appeler le RAG, calculer les scores, écrire les rapports | `uv` installe ses bibliothèques Python dans `.venv/` au premier `uv run` |
| Langfuse | l'outil web où l'on suit chaque évaluation, et où le métier relit les réponses et note celles qui servent à vérifier le juge | `docker compose up -d` démarre 6 conteneurs : l'interface (http://127.0.0.1:3100), son moteur, et ses bases de données (Postgres, ClickHouse, Redis, MinIO) |
| les secrets de Langfuse | ses mots de passe et ses clés d'accès | `./initialiser.sh` les tire au hasard et les écrit dans `.env` |
| l'accès au modèle juge | le juge est un modèle de langage qui compare chaque réponse du RAG à la bonne réponse du métier ; rien ne s'installe, on s'y connecte | sa clé dans `.env` (`KIT_LLM_CLE`), son adresse et son nom dans `config/kit.yaml` |
| la base de données du service | garde tous les résultats, y compris le détail des questions réservées | `resultats/base.sqlite`, créée au premier import |

Les commandes :

```bash
cp .env.example .env
```

Mettre dans `.env` la clé de l'API du modèle juge (`KIT_LLM_CLE`) ; n'importe quel fournisseur compatible OpenAI convient (OpenAI, Mistral, ou un serveur local). Mettre ensuite dans [`config/kit.yaml`](config/kit.yaml) son adresse, le nom des modèles (`modeles` : le juge, et un modèle d'embeddings, dont se servent certains scores de la réponse) et le nom du projet (`projet`). Choisir de préférence pour juge **un autre modèle que celui du RAG** : un modèle tend à favoriser ses propres réponses. Le réglage `sans_reflexion` du juge vaut `false` : l'appel reste standard et marche chez tout fournisseur. Ne le mettre à `true` qu'avec un serveur vLLM ou LiteLLM et un modèle qui raisonne avant de répondre, pour qu'il réponde plus vite ; ailleurs, l'appel serait refusé ([pourquoi](config/README.md)). Puis écrire les secrets de Langfuse et le démarrer :

```bash
./initialiser.sh
```

```bash
docker compose up -d
```

Langfuse est à http://127.0.0.1:3100. L'identifiant est `evaluation@service-evaluation.example`, et le mot de passe est la ligne `LANGFUSE_USER_PASSWORD` de `.env`. Pour vérifier que le juge, le modèle d'embeddings et Langfuse répondent :

```bash
uv run kit verifier-modeles
```

## Les étapes suivantes

Elles sont dans le [fil conducteur](FIL_CONDUCTEUR.md#les-étapes), chacune avec son guide : construire le corpus, ouvrir les endpoints du RAG, évaluer chaque configuration, lire le rapport.

## Essayer avec le corpus d'exemple

Pour essayer le service sans corpus à soi, on lui donne celui de l'exemple, puis on suit les étapes 3 et 4 du [fil conducteur](FIL_CONDUCTEUR.md#3-évaluer-une-configuration-du-rag). Le RAG d'exemple doit être lancé ([son README](../service-rag-exemple/README.md)).

```bash
cp ../service-evaluation-exemple/corpus_annote/corpus_documentaire/*.pdf corpus_annote/corpus_documentaire/
```

```bash
uv run kit importer ../service-evaluation-exemple/corpus_annote/Corpus_evaluation_RAG.xlsx
```

```bash
uv run kit evaluer
```

Vos chiffres peuvent différer de quelques points de ceux de l'exemple : le modèle qui écrit les réponses ne répond pas toujours pareil.

## Les guides, dans l'ordre

Pour un agent de code (Claude Code, Codex, Cursor…) : [AGENTS.md](AGENTS.md) dit quoi faire, dans l'ordre, et ce qu'il ne faut jamais faire.

| Guide | Ce qu'il explique |
| --- | --- |
| [Le fil conducteur](FIL_CONDUCTEUR.md) | par où commencer : ce qu'on fait, dans l'ordre, et le guide de chaque étape |
| [0a. Construction du corpus](documentation/0a_construction_du_corpus.md) | comment le métier annote le corpus, et comment l'importer |
| [0b. Les endpoints du RAG](documentation/0b_endpoints_du_rag.md) | ce que votre RAG doit ouvrir pour être évalué |
| [0c. Les configurations du RAG](documentation/0c_configurations_du_rag.md) | où fixer les réglages du RAG, et comment lancer l'évaluation |
| [1. Évaluation de l'ingestion](documentation/1_evaluation_ingestion.md) | rien ne s'est-il perdu quand le RAG a rangé les documents dans sa base ? |
| [2. Évaluation de la recherche](documentation/2_evaluation_recherche.md) | la recherche ramène-t-elle les morceaux qui contiennent la réponse ? |
| [3. Évaluation de la réponse](documentation/3_evaluation_reponse.md) | la réponse est-elle juste, fondée sur les documents ? |
| [4. Évaluation de bout en bout](documentation/4_evaluation_bout_en_bout.md) | le RAG est-il bon sur ce qui compte, assez rapide, pas trop cher ? Et les scores clés |
| [5. Résultats et comparaison](documentation/5_resultats_et_comparaison.md) | lire un rapport, comparer deux configurations |
| [6. Aide à la décision : lire les scores](documentation/6_aide_a_la_decision.md) | des repères pour lire chaque score et son intervalle de confiance, et présenter les scores à ceux qui décident |
| [Pour aller plus loin : les cas particuliers](documentation/cas_particuliers.md) | un RAG avec un graphe de connaissances, un RAG qui se repose des questions, des réponses qui se calculent sur des données |

## Toutes les commandes

À lancer depuis ce dossier. Chaque commande a son aide : `uv run kit <commande> --help`.

| Commande | Ce qu'elle fait | Guide |
| --- | --- | --- |
| `kit verifier-modeles` | vérifie que le juge, les embeddings et Langfuse répondent | [3. Évaluation de la réponse](documentation/3_evaluation_reponse.md) |
| `kit importer <fichier.xlsx>` | contrôle le fichier du métier (ou un fichier `.json` de même contenu), le range dans `resultats/corpus/`, crée le jeu de questions dans Langfuse | [0a. Construction du corpus](documentation/0a_construction_du_corpus.md) |
| `kit evaluer` | appelle les endpoints du RAG, puis enchaîne les évaluations 1 à 4 ; avec `--boite-noire`, pose seulement les questions à un RAG dont on n'a qu'une API compatible OpenAI, puis fait les évaluations 3 et 4 | [4. Évaluation de bout en bout](documentation/4_evaluation_bout_en_bout.md) |
| `kit appeler-rag` | appelle seulement les endpoints du RAG, et range ses réponses dans `resultats/reponses_du_rag/` | [0b. Les endpoints du RAG : ce que chaque RAG doit fournir](documentation/0b_endpoints_du_rag.md) |
| `kit verifier-contrat <dossier>` | dit précisément ce qui manque dans ce qu'un RAG a rendu | [0b. Les endpoints du RAG : ce que chaque RAG doit fournir](documentation/0b_endpoints_du_rag.md) |
| `kit evaluer-ingestion`, `evaluer-recherche`, `evaluer-reponse`, `evaluer-bout-en-bout` | une évaluation à la fois, sur des réponses déjà rangées | [1. Évaluation de l'ingestion](documentation/1_evaluation_ingestion.md) à [4. Évaluation de bout en bout](documentation/4_evaluation_bout_en_bout.md) |
| `kit verifier-juge [--preparer] [--langfuse]` | `--preparer` écrit le fichier Excel de 30 réponses que le métier note (`--langfuse` : aussi dans Langfuse) ; sans option, lit ses notes, mesure l'accord avec le juge, et le reporte en tête du rapport | [3. Évaluation de la réponse](documentation/3_evaluation_reponse.md) |
| `kit verifier-graphe [--preparer] [--langfuse]` | `--preparer` écrit le fichier Excel de 50 relations du graphe que le métier juge (`--langfuse` : aussi dans Langfuse) ; sans option, dit où il en est | [1. Évaluation de l'ingestion](documentation/1_evaluation_ingestion.md) |
| `kit lire-relecture` | lit la relecture des réponses par le métier (fichier `relecture_reponses.xlsx`, ou Langfuse) et la reporte dans le rapport | [3. Évaluation de la réponse](documentation/3_evaluation_reponse.md) |
| `kit comparer <évaluation A> <évaluation B>` | compare deux configurations déjà évaluées ; écrit son rapport dans `resultats/comparaisons_de_configurations/` | [5. Résultats et comparaison](documentation/5_resultats_et_comparaison.md) |
| `kit init-base` | crée la base de données du service (fait aussi par `importer`) | [0a. Construction du corpus](documentation/0a_construction_du_corpus.md) |

Trois options valent pour les commandes qui évaluent ; `--dossier` vaut pour toutes :

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
