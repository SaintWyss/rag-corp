# Playwright E2E

Este paquete contiene los tests E2E del flujo UI/API.

## Requisitos

- Node.js 20 + pnpm
- Docker + Docker Compose (para modo stack)
- `GOOGLE_API_KEY` configurado si queres respuestas reales del LLM
- Para CI/local sin Google: `FAKE_LLM=1` y `FAKE_EMBEDDINGS=1`

## Instalacion

```bash
cd tests/e2e
pnpm install
pnpm install:browsers
```

## Ejecutar local (dev servers)

Playwright puede levantar backend/frontend segun `playwright.config.ts`.

```bash
# Desde la raiz del repo
pnpm e2e

# Desde tests/e2e
pnpm test
```

## Ejecutar con Docker Compose

```bash
API_KEYS_CONFIG='{"<E2E_API_KEY>":["ingest","ask"]}' \
TEST_API_KEY=<E2E_API_KEY> \
E2E_USE_COMPOSE=1 \
GOOGLE_API_KEY=<GOOGLE_API_KEY> \
docker compose --profile e2e up -d --build

E2E_USE_COMPOSE=1 TEST_API_KEY=<E2E_API_KEY> pnpm e2e

docker compose --profile e2e down -v
```

Para correr `full-pipeline.spec.ts` (upload -> READY -> chat) necesitas storage + worker:

```bash
FAKE_LLM=1 FAKE_EMBEDDINGS=1 \
S3_ENDPOINT_URL=http://minio:9000 \
S3_BUCKET=<S3_BUCKET> \
S3_ACCESS_KEY=<S3_ACCESS_KEY> \
S3_SECRET_KEY=<S3_SECRET_KEY> \
API_KEYS_CONFIG='{"<E2E_API_KEY>":["ingest","ask"]}' \
E2E_ADMIN_EMAIL=<ADMIN_EMAIL> \
E2E_ADMIN_PASSWORD=<ADMIN_PASSWORD> \
pnpm stack:full

pnpm admin:bootstrap -- --email <ADMIN_EMAIL> --password <ADMIN_PASSWORD>
E2E_USE_COMPOSE=1 TEST_API_KEY=<E2E_API_KEY> pnpm e2e -- --project=chromium
```

## Variables usadas

| Variable | Uso |
|---------|-----|
| `TEST_API_KEY` | API key inyectada en sessionStorage para la UI |
| `E2E_USE_COMPOSE` | Desactiva webServer y usa compose | 
| `E2E_BASE_URL` | Base URL del frontend (default http://localhost:3000) |
| `E2E_ADMIN_EMAIL` | Email del admin para login JWT |
| `E2E_ADMIN_PASSWORD` | Password del admin para login JWT |

## Artifacts

Playwright guarda reportes en `tests/e2e/playwright-report` y `tests/e2e/test-results`.
En CI se suben en falla.

## Tests

- `tests/e2e/tests/documents.spec.ts` - Ingesta, listado, detalle y delete
- `tests/e2e/tests/chat.spec.ts` - Chat streaming multi-turn
- `tests/e2e/tests/full-pipeline.spec.ts` - Upload -> READY -> chat (requiere worker + storage)
- `tests/e2e/tests/workspace-flow.spec.ts` - Workspace v6 (HISTORICAL v4 origin, create -> upload -> READY -> chat scoped)
