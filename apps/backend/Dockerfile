# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder

WORKDIR /app

# deps para compilar wheels (psycopg, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


FROM python:3.11-slim AS production

WORKDIR /app

# runtime deps (psql client libs + curl para healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
  && rm -rf /var/lib/apt/lists/* \
  && useradd --create-home --shell /bin/bash appuser

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copiá solo lo necesario (mejor cache y menos mugre)
COPY --chown=appuser:appuser alembic/ ./alembic/
COPY --chown=appuser:appuser alembic.ini ./alembic.ini
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser scripts/ ./scripts/

USER appuser

EXPOSE 8000 8001

# El comando final lo decide compose (backend vs worker vs migrate)
CMD ["python", "-c", "print('Use compose command (apps/backend/worker/migrate)')"]
