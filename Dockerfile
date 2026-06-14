# Образ приложения: Python 3.14, зависимости через uv, запуск api/worker/beat из docker-compose.
FROM python:3.14-slim-bookworm

WORKDIR /app

# libpq — клиент PostgreSQL для psycopg2
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY alembic.ini ./
COPY alembic ./alembic/
COPY app ./app/

# По умолчанию — API; worker и beat переопределяют command в compose
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
