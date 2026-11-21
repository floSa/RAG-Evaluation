# Service RAG d'exemple

Un RAG simple et complet : il lit des documents, les découpe, les indexe, retrouve les bons morceaux pour une question, et rédige une réponse qui cite ses sources. Il ouvre **une porte au service d'évaluation** : quatre portes, à http://127.0.0.1:8100.

C'est un exemple. Il est volontairement minimal, et ses défauts donnent à l'évaluation quelque chose à mesurer. Comment il est construit : [guide du RAG](documentation/guide_du_graphrag.md).

## Lancer le service

Il faut Docker, et un point d'accès à des modèles de langage compatible OpenAI (ici LLM-Service, sur http://127.0.0.1:8080). Depuis `service-rag/` :

```bash
cp .env.example .env
```

Mettre dans `.env` la clé du point d'accès (`RAG_LLM_CLE`). Puis :

```bash
docker compose up -d --build
```

La commande démarre deux conteneurs : le RAG, sa porte ouverte à http://127.0.0.1:8100, et Docling, qui lit les PDF et les scans. Pour vérifier que la porte répond :

```bash
curl -s http://127.0.0.1:8100/index
```

Tant que le service d'évaluation ne lui a rien envoyé, le RAG répond `Aucun document ingéré` : c'est normal. La documentation de chaque porte est à http://127.0.0.1:8100/docs.

Sans Docker, avec Docling démarré à part : `uv run rag ouvrir-porte`.

## Sa porte d'évaluation

Elle est dans [`src/rag/porte_evaluation/`](src/rag/porte_evaluation/), un fichier par porte. C'est la seule partie du RAG écrite pour l'évaluation : si on la supprime, le RAG marche toujours.

| Porte | Fichier | Ce qu'elle fait |
| --- | --- | --- |
| ① ingérer | [`ingerer.py`](src/rag/porte_evaluation/ingerer.py) | reçoit les documents de l'évaluation, et les indexe à part de la production (`sorties/evaluation/`) |
| ② montrer l'index | [`montrer_index.py`](src/rag/porte_evaluation/montrer_index.py) | rend la version exacte du RAG, ses morceaux de texte, les pages lues, son graphe |
| ③ rechercher | [`rechercher.py`](src/rag/porte_evaluation/rechercher.py) | rend les k morceaux retrouvés pour une question |
| ④ répondre | [`repondre.py`](src/rag/porte_evaluation/repondre.py) | rend la réponse, ses sources, et si le RAG s'abstient |

La règle que chaque RAG doit suivre : [la porte du RAG](../service-evaluation/documentation/0b_porte_du_rag.md).

## Lancer une autre version

Pour comparer deux réglages, on relance le service avec un autre réglage, puis on évalue de nouveau :

```bash
RAG_K=3 docker compose up -d
```

```bash
RAG_GRAPHE=true docker compose up -d
```

Le premier donne 3 morceaux au modèle au lieu de 5 ; le second allume le graphe (le RAG devient « hybride »). Les autres réglages sont dans [`config/config.yaml`](config/config.yaml) ; après un changement : `docker compose restart rag`.

## S'en servir seul

Une fois que le service d'évaluation lui a envoyé ses documents :

```bash
uv run rag demander "Combien de temps faut-il pour consigner une armoire divisionnaire ?" --espace evaluation
```

Avec `--profil maintenance`, la question est posée par un utilisateur du profil Maintenance, qui voit aussi ses documents réservés. En production, on met ses documents dans [`documents/`](documents/), puis `uv run rag indexer`.

## Arrêter

```bash
docker compose down
```

L'index reste dans `sorties/`.

## Tests

```bash
uv run pytest -q
```
