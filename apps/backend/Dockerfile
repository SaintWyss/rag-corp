# ============================================================
# TARJETA CRC (Class / Responsibilities / Collaborators)
# ============================================================
# Class: apps/backend/Dockerfile (Build + Runtime de backend/worker/migrate)
#
# Responsibilities:
# - Construir wheels (stage builder) para dependencias Python con extensiones nativas
#   (ej: psycopg/psycopg2, etc.) usando toolchain de compilación.
# - Generar una imagen final liviana (stage production) con:
#   - solo librerías runtime necesarias (libpq5, curl)
#   - usuario no-root
#   - código mínimo (app + alembic + scripts)
# - Dejar el ENTRYPOINT/command al orquestador (compose) para elegir:
#   - API (uvicorn)
#   - worker
#   - migrate (alembic)
#
# Collaborators:
# - pip / wheels
# - PostgreSQL client libraries (libpq)
# - Alembic (migrations)
# - Uvicorn/FastAPI (API runtime)
# ============================================================

# syntax=docker/dockerfile:1

# ============================================================
# STAGE 1: builder
# - Compila wheels (dependencias) para acelerar installs posteriores
#   y evitar compilar en la imagen final.
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# ----------------------------
# Dependencias de build
# - gcc: compilar extensiones C
# - libpq-dev: headers para clientes PostgreSQL (psycopg/psycopg2)
# ----------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
  gcc libpq-dev \
  && rm -rf /var/lib/apt/lists/*

# Copiamos solo requirements para maximizar cache:
# si el código cambia pero requirements no, no recompila wheels.
COPY requirements.txt .

# Construye wheels en /wheels para instalar luego sin compilar
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


# ============================================================
# STAGE 2: production
# - Runtime liviano y seguro (usuario no-root)
# - Instala wheels precompilados
# ============================================================
FROM python:3.11-slim AS production

WORKDIR /app

# ----------------------------
# Dependencias de runtime
# - libpq5: librerías runtime para PostgreSQL
# - curl: útil para healthchecks (si elegís curl en compose)
# - useradd: crea usuario no-root (appuser)
# ----------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
  libpq5 curl \
  && rm -rf /var/lib/apt/lists/* \
  && useradd --create-home --shell /bin/bash appuser

# Copiamos wheels desde builder e instalamos sin cache
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# ----------------------------
# Copiamos solo lo necesario:
# - alembic/ + alembic.ini (migraciones)
# - app/ (código principal)
# - scripts/ (utilidades: bootstrap admin, export OpenAPI, etc.)
# Usamos --chown para evitar permisos root.
# ----------------------------
COPY --chown=appuser:appuser alembic/ ./alembic/
COPY --chown=appuser:appuser alembic.ini ./alembic.ini
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser scripts/ ./scripts/

# Ejecutar como usuario no-root (más seguro)
USER appuser

# Exponemos puertos típicos:
# - 8000: API
# - 8001: worker HTTP (si tu worker expone /readyz)
EXPOSE 8000 8001

# Este CMD es “placeholder”.
# El comando real lo define docker compose:
# - API: uvicorn ...
# - worker: python -m app.worker.worker
# - migrate: alembic upgrade head
CMD ["python", "-c", "print('Use compose command (apps/backend/api/worker/migrate)')"]