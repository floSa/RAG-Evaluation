#!/usr/bin/env bash
# Ajoute à service-evaluation/.env les secrets de Langfuse (tirés au hasard) et les clés de son projet,
# lus par docker compose et par le kit. Ne fait rien si .env les contient déjà.
# Usage, depuis service-evaluation/ : ./initialiser.sh
set -euo pipefail
cd "$(dirname "$0")"

[ -f .env ] || cp .env.example .env
if grep -q "^POSTGRES_PASSWORD=" .env; then
  echo ".env contient déjà les secrets de Langfuse : rien à faire."
  exit 0
fi

hasard() { head -c 48 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | cut -c1-32; }
chmod 600 .env
cat >> .env <<FIN

# Langfuse (écrit par initialiser.sh)
POSTGRES_PASSWORD=$(hasard)
CLICKHOUSE_PASSWORD=$(hasard)
REDIS_PASSWORD=$(hasard)
MINIO_ROOT_PASSWORD=$(hasard)
SALT=$(hasard)
NEXTAUTH_SECRET=$(hasard)
ENCRYPTION_KEY=$(openssl rand -hex 32)
LANGFUSE_BASE_URL=http://127.0.0.1:3100
LANGFUSE_PUBLIC_KEY=pk-lf-$(hasard)
LANGFUSE_SECRET_KEY=sk-lf-$(hasard)
LANGFUSE_USER_EMAIL=evaluation@service-evaluation.example
LANGFUSE_USER_PASSWORD=$(hasard)
FIN
echo "Secrets de Langfuse ajoutés à .env. Compte : evaluation@service-evaluation.example (mot de passe : LANGFUSE_USER_PASSWORD dans .env)."
