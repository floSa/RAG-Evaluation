# Le RAG d'exemple, avec ses endpoints d'évaluation ouverts (rag ouvrir-endpoints).
FROM python:3.12-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /bin/uv
WORKDIR /service

# Les dépendances d'abord : elles changent rarement, Docker les garde en cache
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY config ./config
RUN uv sync --frozen --no-dev

CMD ["/service/.venv/bin/rag", "ouvrir-endpoints"]
