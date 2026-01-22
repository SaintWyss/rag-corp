#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.prod.local}"
COMPOSE_BASE="compose.prod.yaml"
COMPOSE_LOCAL="compose.prod.local.yaml"

dc() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_BASE" -f "$COMPOSE_LOCAL" "$@"
}

echo "== ps =="
dc ps

echo "== health checks =="
curl -sf http://localhost:8000/healthz >/dev/null && echo "API health OK"
curl -sf http://localhost:8000/readyz  >/dev/null && echo "API ready OK"
curl -sf http://localhost:8001/readyz  >/dev/null && echo "Worker ready OK"
curl -sf http://localhost:3000         >/dev/null && echo "Frontend OK"

echo "== metrics (requires API key) =="
curl -sf -H 'X-API-Key: prod-local' http://localhost:8000/metrics | head -n 5

echo "ALL OK"
