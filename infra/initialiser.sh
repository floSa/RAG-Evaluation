#!/usr/bin/env bash
# Crée infra/.env (secrets de Langfuse, tirés au hasard) et recopie les clés du projet Langfuse
# dans le .env du dépôt, lu par le kit et le RAG. Ne fait rien si infra/.env existe déjà.
# Usage : infra/initialiser.sh
set -euo pipefail
cd "$(dirname "$0")"

if [ -f .env ]; then
  echo "infra/.env existe déjà : rien à faire."
  exit 0
fi

hasard() { head -c 48 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | cut -c1-32; }
CLE_PUBLIQUE="pk-lf-$(hasard)"
CLE_SECRETE="sk-lf-$(hasard)"
MOT_DE_PASSE="$(hasard)"

umask 077
cat > .env <<EOF
# Secrets de Langfuse, générés par infra/initialiser.sh (jamais versionné)
POSTGRES_PASSWORD=$(hasard)
CLICKHOUSE_PASSWORD=$(hasard)
REDIS_PASSWORD=$(hasard)
MINIO_ROOT_PASSWORD=$(hasard)
SALT=$(hasard)
NEXTAUTH_SECRET=$(hasard)
ENCRYPTION_KEY=$(openssl rand -hex 32)
LANGFUSE_PUBLIC_KEY=$CLE_PUBLIQUE
LANGFUSE_SECRET_KEY=$CLE_SECRETE
LANGFUSE_USER_EMAIL=evaluation@valtera.example
LANGFUSE_USER_PASSWORD=$MOT_DE_PASSE
EOF

# Clés du projet Langfuse pour le kit et le RAG (.env du dépôt)
RACINE_ENV=../.env
touch "$RACINE_ENV"
sed -i '/^LANGFUSE_\(BASE_URL\|HOST\|PUBLIC_KEY\|SECRET_KEY\)=/d' "$RACINE_ENV"
cat >> "$RACINE_ENV" <<EOF

# Langfuse du bac à sable (écrit par infra/initialiser.sh)
LANGFUSE_BASE_URL=http://127.0.0.1:3100
LANGFUSE_PUBLIC_KEY=$CLE_PUBLIQUE
LANGFUSE_SECRET_KEY=$CLE_SECRETE
EOF

echo "infra/.env créé. Compte Langfuse : evaluation@valtera.example (mot de passe dans infra/.env)."
