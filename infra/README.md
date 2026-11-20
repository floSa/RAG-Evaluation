# Les services : Langfuse et Docling

| Service | Adresse | Rôle | Utilisé par |
| --- | --- | --- | --- |
| Langfuse v4 (web, worker, PostgreSQL, ClickHouse, Redis, MinIO) | http://127.0.0.1:3100 | jeu de questions, traces, expériences, scores, files de relecture du métier | le kit ; le RAG pour ses traces |
| Docling-serve | http://127.0.0.1:5101 | lecture des PDF : mise en page, tableaux, OCR des scans | le RAG de démonstration seulement |

Les modèles de langage ne sont pas ici : le kit et le RAG appellent un point d'accès compatible OpenAI, configuré dans leur propre fichier.

## Premier démarrage

```bash
infra/initialiser.sh
```

La commande crée `infra/.env` avec des secrets tirés au hasard, le compte Langfuse et les clés du projet. Elle recopie aussi `LANGFUSE_BASE_URL`, `LANGFUSE_PUBLIC_KEY` et `LANGFUSE_SECRET_KEY` dans le `.env` du dépôt. Aucun de ces fichiers n'est versionné.

```bash
docker compose -f infra/docker-compose.yml --env-file infra/.env up -d
```

Connexion à Langfuse : l'adresse `evaluation@valtera.example`, le mot de passe se trouve dans `infra/.env` (`LANGFUSE_INIT_USER_PASSWORD`).

## Vérifier

```bash
curl -s http://127.0.0.1:3100/api/public/health
```

```bash
curl -s http://127.0.0.1:5101/health
```

```bash
uv run kit verifier-modeles
```

## Arrêter

```bash
docker compose -f infra/docker-compose.yml --env-file infra/.env down
```

Les données (traces, scores, notes du métier) restent dans les volumes Docker. Ajouter `-v` les efface.
