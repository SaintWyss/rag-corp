#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# TARJETA CRC - tests/e2e/scripts/run-e2e.sh (Runner E2E Compose + Playwright)
# =============================================================================
# Responsabilidades:
# - Levantar stack E2E con Docker Compose.
# - Ejecutar Playwright con base URL estable.
# - Forzar backend URL interna de red Docker para evitar drift.
#
# Colaboradores:
# - docker compose (perfil e2e)
# - Playwright (tests/e2e)
#
# Invariantes:
# - No imprimir secretos ni valores sensibles.
# - Usar http://rag-api:8000 como backend interno para rewrites.
# =============================================================================

# Defaults (permitiendo override para Admin creds)
export E2E_ADMIN_EMAIL="${E2E_ADMIN_EMAIL:-admin@local}"
export E2E_ADMIN_PASSWORD="${E2E_ADMIN_PASSWORD:-admin}"
export E2E_SEED_ADMIN=1
# Forzar estos para garantizar funcionamiento del script
export E2E_USE_COMPOSE=1
export E2E_BASE_URL="http://localhost:3000"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
E2E_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

echo "🚀 Run E2E | Repo: $REPO_ROOT"

# 1) Ir al root y levantar docker
cd "$REPO_ROOT"

echo "🐳 Starting Docker..."
# Forzamos backend interno de red Docker para evitar proxy a localhost.
RAG_BACKEND_URL="http://rag-api:8000" docker compose --profile e2e up -d --build db rag-api web

# 2) Esperar web
echo "⏳ Waiting for Web ($E2E_BASE_URL/login)..."
WEB_OK=0
# 60s timeout
for i in $(seq 1 60); do
  # Check status code 2xx or 3xx
  STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$E2E_BASE_URL/login" || echo "000")
  if [[ "$STATUS_CODE" =~ ^[23] ]]; then
    WEB_OK=1
    break
  fi
  
  if [ $((i % 5)) -eq 0 ]; then
     echo "   ... waiting ($i/60s) [Last status: $STATUS_CODE]"
  fi
  sleep 1
done

if [ "$WEB_OK" -ne 1 ]; then
  echo "❌ Web failed to start or respond 200/3xx in 60s."
  echo "--- Docker PS ---"
  docker compose --profile e2e ps || true
  echo "--- Web Logs ---"
  docker compose --profile e2e logs web --tail=200 || true
  echo "--- API Logs (Critical for 500 errors) ---"
  docker compose --profile e2e logs rag-api --tail=200 || true
  exit 1
fi

echo "✅ Web is UP."

# 3) Run tests inside e2e dir
cd "$E2E_DIR"
echo "📦 Installing E2E deps..."
pnpm install

echo "🎭 Checking browsers..."
pnpm exec playwright install chromium

echo "🧪 Running Tests..."
set +e
# Playwright usará E2E_USE_COMPOSE=1, asi que no levantará sus webservers (usará el docker que ya levantamos)
pnpm exec playwright test -c playwright.config.cjs --project=chromium --timeout=60000
TEST_EXIT_CODE=$?
set -e

if [ "$TEST_EXIT_CODE" -ne 0 ]; then
  echo "❌ Tests failed (exit $TEST_EXIT_CODE)."
  # Imprimir logs de API para debug
  echo "🔍 Dumping API logs for debug..."
  cd "$REPO_ROOT"
  docker compose --profile e2e logs rag-api --tail=100 || true
else
  echo "✅ Tests passed."
fi

exit "$TEST_EXIT_CODE"
