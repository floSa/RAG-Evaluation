# Service RAG, exemple

Ce dossier est **un RAG simple, qui sert d'exemple à évaluer**. Il montre comment un RAG se branche sur le [service d'évaluation](../service-evaluation/README.md) : en ouvrant quatre endpoints. Les résultats de son évaluation sont dans [`service-evaluation-exemple/`](../service-evaluation-exemple/README.md).

Il est volontairement minimal : le sujet du dépôt est l'évaluation, et ses défauts donnent à l'évaluation quelque chose à mesurer.

## Ce qu'il fait

Un RAG répond à des questions en s'appuyant sur des documents. Celui-ci le fait en six étapes :

1. **Lire** les documents, y compris les pages scannées et les tableaux, avec Docling.
2. **Découper** chaque document en morceaux de texte (les *chunks*), section par section.
3. **Ranger** ces morceaux dans une base vectorielle : chacun est transformé en vecteur, qui représente son sens.
4. **Construire un graphe**, s'il est activé : les liens entre équipements, sites et personnes, extraits des documents.
5. **Rechercher**, pour une question, les k morceaux les plus proches : par le sens et par les mots, en écartant les documents que la personne n'a pas le droit de voir.
6. **Répondre** : un modèle de langage écrit la réponse à partir de ces morceaux, cite ses sources, et dit « je ne sais pas » si les morceaux ne suffisent pas.

## Ses quatre endpoints d'évaluation

Le service d'évaluation appelle ces quatre adresses web, à http://127.0.0.1:8100 :

| Endpoint | Ce qu'il fait |
| --- | --- |
| ① `POST /ingerer` | reçoit les documents de l'évaluation, et les range à part de son propre corpus documentaire |
| ② `GET /index` | rend la version exacte du RAG, ses morceaux de texte, les pages lues, et son graphe |
| ③ `POST /rechercher` | pour une question, rend les k morceaux retrouvés |
| ④ `POST /repondre` | pour une question, rend la réponse, ses sources, et s'il s'abstient |

Leur code est dans [`src/rag/endpoints_evaluation/`](src/rag/endpoints_evaluation/). C'est la seule partie du RAG écrite pour l'évaluation : si on la supprime, le RAG marche toujours. La règle que chaque RAG doit suivre : [0b. Les endpoints du RAG : ce que chaque RAG doit fournir](../service-evaluation/documentation/0b_endpoints_du_rag.md).

## Ce qu'il y a dans ce dossier

| Dossier | À quoi il sert |
| --- | --- |
| [`config/`](config/) | ses réglages : les modèles, le nombre de morceaux ramenés (k), le graphe activé ou non, l'adresse des endpoints |
| [`src/rag/`](src/rag/) | son code : `pipeline/`, les six étapes du RAG ; `endpoints_evaluation/`, les quatre endpoints |
| [`corpus_documentaire/`](corpus_documentaire/) | ce que le RAG lit quand il sert ses utilisateurs : ici un dossier de fichiers, ailleurs une autre source (GED, base de données, application). Vide ici : le RAG d'exemple ne lit que ce que le service d'évaluation lui envoie |
| [`documentation/`](documentation/) | comment il est construit, et les techniques d'un RAG |
| [`tests/`](tests/) | les tests de son code |

Les fichiers à la racine servent à le lancer : `docker-compose.yml` démarre le RAG et Docling ; `Dockerfile` construit l'image du RAG ; `pyproject.toml` et `uv.lock` listent ses bibliothèques Python ; `.env.example` montre la clé à fournir.

## Le lancer

Il faut Docker, et un accès à des modèles de langage par une API compatible OpenAI. Depuis ce dossier :

```bash
cp .env.example .env
```

Mettre dans `.env` la clé de l'API des modèles (`RAG_LLM_CLE`), puis :

```bash
docker compose up -d --build
```

La commande démarre deux conteneurs : le RAG, avec ses endpoints ouverts à http://127.0.0.1:8100, et Docling, qui lit les PDF et les scans. Pour vérifier que les endpoints répondent :

```bash
curl -s http://127.0.0.1:8100/index
```

Tant que le service d'évaluation ne lui a rien envoyé, le RAG répond `Aucun document ingéré` : c'est normal. La description de chaque endpoint est à http://127.0.0.1:8100/docs.

## Changer de configuration

Une configuration, c'est le RAG avec tous ses réglages fixés. Pour en évaluer une autre, on relance le RAG avec un autre réglage, puis on relance l'évaluation (`uv run kit evaluer`, dans `service-evaluation/`) :

| Pour… | Commande |
| --- | --- |
| ramener 3 morceaux par question au lieu de 5 | `RAG_K=3 docker compose up -d` |
| ajouter le graphe (le RAG devient « hybride ») | `RAG_GRAPHE=true docker compose up -d` |
| revenir à la configuration de référence | `docker compose up -d` |

Les autres réglages sont dans [`config/config.yaml`](config/config.yaml) ; après un changement : `docker compose restart rag`.

## S'en servir seul

Une fois que le service d'évaluation lui a envoyé ses documents :

```bash
uv run rag demander "Combien de temps faut-il pour consigner une armoire divisionnaire ?" --espace evaluation
```

Avec `--profil maintenance`, la question est posée par un utilisateur du profil Maintenance, qui voit aussi les documents réservés à ce profil.

## Arrêter

```bash
docker compose down
```

Sa base vectorielle reste dans `sorties/`, un dossier de travail non versionné.

## Tests

```bash
uv run pytest -q
```
