#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# TARJETA CRC - scripts/e2e/run_e2e.sh (Runner E2E local/CI)
# =============================================================================
# Responsabilidades:
# - Levantar el stack E2E con Docker Compose.
# - Bootstrappear un admin de pruebas (no sensible).
# - Ejecutar Playwright E2E con envs deterministas.
# - Limpiar el stack si no se solicita lo contrario.
#
# Colaboradores:
# - tests/e2e/*
# - apps/backend/scripts/create_admin.py
# - compose.yaml
#
# Invariantes:
# - No imprimir secretos en logs.
# - No usar credenciales reales.
# =============================================================================

log() {
  echo "[e2e] $*"
}

die() {
  echo "[e2e] ERROR: $*" >&2
  exit 1
}

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    die "Docker no disponible en PATH."
  fi
  if ! docker info >/dev/null 2>&1; then
    die "Docker no esta corriendo."
  fi
}

load_env_file() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    return 0
  fi
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    [[ "$line" =~ ^# ]] && continue
    if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
      export "$line"
    fi
  done < "$file"
}

DEFAULT_ADMIN_EMAIL="admin@local"
DEFAULT_ADMIN_PASSWORD="admin"
DEFAULT_API_KEYS_CONFIG='{"e2e-key":["ingest","ask"]}'
DEFAULT_TEST_API_KEY="e2e-key"

# Carga envs deterministas (si existen)
load_env_file "tests/e2e/.env.e2e"
load_env_file "tests/e2e/.env.e2e.example"

export E2E_ADMIN_EMAIL="${E2E_ADMIN_EMAIL:-$DEFAULT_ADMIN_EMAIL}"
export E2E_ADMIN_PASSWORD="${E2E_ADMIN_PASSWORD:-$DEFAULT_ADMIN_PASSWORD}"
export E2E_USE_COMPOSE="${E2E_USE_COMPOSE:-1}"
export E2E_BASE_URL="${E2E_BASE_URL:-http://localhost:3000}"
export E2E_API_URL="${E2E_API_URL:-http://localhost:8000}"
export API_KEYS_CONFIG="${API_KEYS_CONFIG:-$DEFAULT_API_KEYS_CONFIG}"
export TEST_API_KEY="${TEST_API_KEY:-$DEFAULT_TEST_API_KEY}"
export FAKE_LLM="${FAKE_LLM:-1}"
export FAKE_EMBEDDINGS="${FAKE_EMBEDDINGS:-1}"
export REDIS_URL="${REDIS_URL:-redis://redis:6379}"
export S3_ENDPOINT_URL="${S3_ENDPOINT_URL:-http://minio:9000}"
export S3_ACCESS_KEY="${S3_ACCESS_KEY:-minioadmin}"
export S3_SECRET_KEY="${S3_SECRET_KEY:-minioadmin}"
export S3_BUCKET="${S3_BUCKET:-rag-documents}"
export S3_REGION="${S3_REGION:-us-east-1}"
export MINIO_ROOT_USER="${MINIO_ROOT_USER:-minioadmin}"
export MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minioadmin}"
export RATE_LIMIT_RPS="${RATE_LIMIT_RPS:-500}"
export RATE_LIMIT_BURST="${RATE_LIMIT_BURST:-1000}"
export DB_HEALTHCHECK_ON_ACQUIRE="${DB_HEALTHCHECK_ON_ACQUIRE:-false}"

require_docker

cleanup() {
  if [[ "${E2E_KEEP_STACK:-0}" == "1" ]]; then
    log "E2E_KEEP_STACK=1 -> no se baja el stack."
    return 0
  fi
  docker compose --profile e2e --profile rag down -v --remove-orphans
}
trap cleanup EXIT

log "Levantando stack E2E..."
# Forzar backend interno de red Docker para rewrites del frontend.
export RAG_BACKEND_URL="http://rag-api:8000"
RAG_BACKEND_URL="$RAG_BACKEND_URL" docker compose --profile e2e --profile rag up -d --build

log "Esperando /healthz backend..."
for _ in {1..30}; do
  if curl -sf "http://localhost:8000/healthz" >/dev/null; then
    break
  fi
  sleep 2
done
curl -sf "http://localhost:8000/healthz" >/dev/null

log "Esperando frontend..."
for _ in {1..30}; do
  if curl -sf "http://localhost:3000" >/dev/null; then
    break
  fi
  sleep 2
done
curl -sf "http://localhost:3000" >/dev/null

log "Bootstrap admin E2E (no sensible)..."
docker compose exec -T rag-api \
  python scripts/create_admin.py \
  --email "$E2E_ADMIN_EMAIL" \
  --password "$E2E_ADMIN_PASSWORD"

log "Ejecutando Playwright E2E..."
E2E_USE_COMPOSE="1" pnpm e2e

log "E2E completado."
