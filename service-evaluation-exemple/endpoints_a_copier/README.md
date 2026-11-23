# Les endpoints à copier dans votre RAG

Pour être évalué, un RAG ouvre **quatre endpoints**, quatre adresses web de forme fixe que le service appelle. Ce dossier en donne le code, à copier dans votre RAG.

| Élément | À quoi il sert |
| --- | --- |
| [`endpoints_evaluation.py`](endpoints_evaluation.py) | les quatre endpoints : ① ingérer les documents, ② montrer l'index, ③ rechercher, ④ répondre. Tel quel, il fait tourner un RAG jouet, pour voir la forme exacte de chaque endpoint. Pour votre RAG, on remplace seulement les fonctions marquées « À REMPLACER » |

Le lancer tel quel, depuis ce dossier :

```bash
uv run --with fastapi --with uvicorn --with pypdf uvicorn endpoints_evaluation:app --host 127.0.0.1 --port 8100
```

La règle complète : [guide 0b](../documentation/0b_endpoints_du_rag.md). Le pas à pas : [guide 0b, côté RAG](../documentation/0b_endpoints_du_rag.md#3-côté-rag--où-ranger-les-endpoints). Un RAG complet qui les ouvre : [`service-rag-exemple/`](../../service-rag-exemple/README.md).
