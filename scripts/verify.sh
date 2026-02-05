#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# TARJETA CRC - scripts/verify.sh (Release verification unificado)
# =============================================================================
# Responsabilidades:
# - Ejecutar verificacion local end-to-end en orden estable.
# - Reutilizar scripts oficiales del repo (secrets, contracts, kustomize, e2e).
# - Fallar rapido con mensajes claros y sin exponer secretos.
#
# Colaboradores:
# - scripts/security/verify_no_secrets.sh
# - infra/k8s/render_kustomize.sh
# - scripts/e2e/run_e2e.sh
# - package.json (script pnpm verify)
#
# Invariantes:
# - No imprimir secretos ni valores sensibles.
# - No cambiar archivos del repo.
# =============================================================================

log() {
  echo "[verify] $*"
}

die() {
  echo "[verify] ERROR: $*" >&2
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

log "1) Secret scan"
bash scripts/security/verify_no_secrets.sh

log "2) Contracts export + gen"
require_docker
pnpm contracts:export
pnpm contracts:gen

log "3) Frontend check (lint + typecheck + tests)"
pnpm -C apps/frontend check

log "4) Backend tests"
DB_STARTED=0
if ! docker compose ps -q db >/dev/null 2>&1 || [[ -z "$(docker compose ps -q db)" ]]; then
  log "Levantando Postgres local (compose) para tests..."
  docker compose up -d db
  DB_STARTED=1
fi

export DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/rag}"
(
  cd apps/backend
  pytest -q
)

if [[ "$DB_STARTED" == "1" && "${VERIFY_KEEP_STACK:-0}" != "1" ]]; then
  log "Deteniendo Postgres local..."
  docker compose stop db
fi

log "5) Docker builds (backend + frontend)"
docker build -f apps/backend/Dockerfile apps/backend
docker build -f apps/frontend/Dockerfile apps/frontend

log "6) Kustomize render (staging + prod)"
bash infra/k8s/render_kustomize.sh staging --out /tmp/ragcorp-staging.yaml
bash infra/k8s/render_kustomize.sh prod --out /tmp/ragcorp-prod.yaml
if grep -n ":latest" /tmp/ragcorp-prod.yaml; then
  die "Prod render contiene :latest. Usar tags inmutables."
fi

log "7) E2E smoke"
bash scripts/e2e/run_e2e.sh

log "Verificacion completa."
