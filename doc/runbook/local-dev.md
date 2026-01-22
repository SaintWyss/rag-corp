# Local Development Runbook

**Project:** RAG Corp  
**Last Updated:** 2026-01-22

---

## Quickstart

```bash
# 1) Configure environment
cp .env.example .env
# Edit .env and set GOOGLE_API_KEY

# 2) Install dependencies
pnpm install

# 3) Start services (db + api)
pnpm docker:up

# 3.1) Apply migrations explicitly (idempotent)
pnpm db:migrate

# 3.2) Bootstrap admin (optional, for UI login)
pnpm admin:bootstrap -- --email <ADMIN_EMAIL> --password <ADMIN_PASSWORD>

# 4) Export contracts (OpenAPI -> TS)
pnpm contracts:export
pnpm contracts:gen

# 5) Start frontend dev server
pnpm dev
```

**Access:**
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

---

## Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Si no tenes Google API key, usa providers fake:

```bash
export FAKE_LLM=1 FAKE_EMBEDDINGS=1
```

Export OpenAPI locally:

```bash
cd backend
python3 scripts/export_openapi.py --out ../shared/contracts/openapi.json
```

---

## Frontend (Next.js)

```bash
cd frontend
pnpm dev
```

El frontend consume `/api/*` (proxy a `/v1/*`) y `/auth/*` (JWT).

---

## Docker Compose

```bash
# Start only DB
docker compose up -d db

# Stop DB
docker compose stop db

# Reset DB (data loss)
docker compose down -v

# Connect via psql
docker compose exec db psql -U postgres -d rag
```

### Canonical full stack + migrations

```bash
# 1) Start full stack (db + api + redis + minio + worker)
pnpm stack:full

# 2) Apply migrations (explicit, idempotent)
pnpm db:migrate
```

Bootstrap admin (idempotent):

```bash
pnpm admin:bootstrap -- --email <ADMIN_EMAIL> --password <ADMIN_PASSWORD>
```

Para storage local con MinIO (profile `full`), exporta:

```bash
export S3_ENDPOINT_URL=http://minio:9000
export S3_BUCKET=<S3_BUCKET>
export S3_ACCESS_KEY=<S3_ACCESS_KEY>
export S3_SECRET_KEY=<S3_SECRET_KEY>
```

Si corres el backend fuera de Docker, usa `http://localhost:9000`.

### Web container for E2E

```bash
# Start db + rag-api + web
docker compose --profile e2e up -d --build
```

---

## Environment Variables

```
DATABASE_URL=postgresql://<DB_USER>:<DB_PASSWORD>@localhost:5432/<DB_NAME>
GOOGLE_API_KEY=<GOOGLE_API_KEY>
FAKE_LLM=1
FAKE_EMBEDDINGS=1
NEXT_PUBLIC_API_URL=http://localhost:8000
API_KEYS_CONFIG=
RBAC_CONFIG=
METRICS_REQUIRE_AUTH=false
JWT_SECRET=<JWT_SECRET>
JWT_ACCESS_TTL_MINUTES=30
JWT_COOKIE_NAME=access_token
JWT_COOKIE_SECURE=false
EMBEDDING_CACHE_BACKEND=memory
REDIS_URL=
S3_ENDPOINT_URL=
S3_BUCKET=
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_REGION=
MAX_UPLOAD_BYTES=26214400
MAX_CONVERSATION_MESSAGES=12
```

---

## Bootstrap Admin

Crear el primer admin (idempotente):

```bash
pnpm admin:bootstrap -- --email <ADMIN_EMAIL> --password <ADMIN_PASSWORD>
```

Alternativas:

```bash
cd backend
python3 scripts/create_admin.py --email <ADMIN_EMAIL>

docker compose run --rm rag-api python scripts/create_admin.py --email <ADMIN_EMAIL>
```

---

## Cache (Redis)

Redis se usa para cache de embeddings y cola del worker (cuando `REDIS_URL` esta configurado).

### In-Memory (Default)

Sin configuracion adicional. Ideal para desarrollo local:
- LRU con maximo 1000 entradas
- TTL interno de 1 hora
- Se pierde al reiniciar el servidor

### Redis (Opcional)

```bash
# 1) Configurar en .env
EMBEDDING_CACHE_BACKEND=redis
REDIS_URL=redis://localhost:6379

# 2) Levantar Redis standalone
docker run -d -p 6379:6379 --name redis redis:7-alpine

# 3) O usar compose con perfil full
pnpm stack:full
```

---

## Testing

### Backend Tests

```bash
# Unit tests (Docker, recomendado)
pnpm test:backend:unit

# Unit tests (offline)
cd backend
pytest -m unit

# Si no hay GOOGLE_API_KEY
FAKE_LLM=1 FAKE_EMBEDDINGS=1 pytest -m unit

# Integration tests (requires DB + GOOGLE_API_KEY)
RUN_INTEGRATION=1 GOOGLE_API_KEY=your-key pytest -m integration

# All tests (integration skipped unless RUN_INTEGRATION=1)
pytest
```

### Frontend Tests

```bash
cd frontend

# Run all tests
pnpm test

# Run tests in watch mode (for development)
pnpm test:watch

# Run with coverage report (must meet 70% threshold)
pnpm test:coverage
```

### E2E Tests (Playwright)

```bash
# Install Playwright browsers (first time only)
pnpm e2e:install
pnpm e2e:install:browsers

# Run E2E (local dev servers)
pnpm e2e

# Run E2E with Docker Compose stack
E2E_USE_COMPOSE=1 TEST_API_KEY=<E2E_API_KEY> pnpm e2e
```

Tests:
- `tests/e2e/tests/documents.spec.ts`
- `tests/e2e/tests/chat.spec.ts`
- `tests/e2e/tests/full-pipeline.spec.ts`
- `tests/e2e/tests/workspace-flow.spec.ts`

Nota: el backend debe tener `API_KEYS_CONFIG` con la key usada en `TEST_API_KEY`.

---

## Observability

### Starting Observability Stack

```bash
# Start with observability profile (Prometheus + Grafana)
pnpm docker:observability

# Or start everything (db + api + redis + observability)
pnpm stack:full
```

**URLs:**
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001 (admin/admin)
- Postgres Exporter: http://localhost:9187/metrics

### Metrics

`/metrics` es publico solo si `METRICS_REQUIRE_AUTH=false`. En prod debe estar protegido.

Metricas relevantes:
- `rag_requests_total`
- `rag_request_latency_seconds`
- `rag_embed_latency_seconds`
- `rag_retrieve_latency_seconds`
- `rag_llm_latency_seconds`
- `rag_embedding_cache_hit_total`
- `rag_embedding_cache_miss_total`
- `rag_worker_processed_total`
- `rag_worker_failed_total`
- `rag_worker_duration_seconds`

### Logs Estructurados (JSON)

Los logs del backend son JSON con campos automaticos:

```json
{
  "timestamp": "2026-01-03T12:00:00.000Z",
  "level": "INFO",
  "message": "query answered",
  "request_id": "abc-123-def-456",
  "method": "POST",
  "path": "/v1/ask",
  "embed_ms": 45.2,
  "retrieve_ms": 12.3,
  "llm_ms": 234.5,
  "total_ms": 291.9,
  "chunks_found": 3
}
```

**Campos de contexto:**

| Campo | Descripcion |
|-------|-------------|
| `request_id` | UUID unico por request (correlacion) |
| `trace_id` | OpenTelemetry trace ID (si habilitado) |
