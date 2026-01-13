# Local Development Runbook

**Project:** RAG Corp  
**Last Updated:** 2026-01-03

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

# 4) Export contracts (OpenAPI -> TS)
pnpm contracts:export
pnpm contracts:gen

# 5) Start dev servers
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
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
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

---

## Database

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

---

## Environment Variables

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag
GOOGLE_API_KEY=your-google-api-key-here
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Cache (Redis)

El backend soporta dos backends de cache para embeddings:

### In-Memory (Default)

Sin configuración adicional. Ideal para desarrollo local:
- LRU con máximo 1000 entradas
- TTL de 1 hora
- Se pierde al reiniciar el servidor

### Redis (Producción)

```bash
# 1) Configurar en .env
REDIS_URL=redis://localhost:6379

# 2) Opción A: Levantar Redis standalone
docker run -d -p 6379:6379 --name redis redis:7-alpine

# 2) Opción B: Usar docker compose con perfil full
pnpm docker:full
# Esto levanta: db + api + redis
```

**Verificar conexión:**
```bash
docker exec redis redis-cli ping
# Esperado: PONG
```

**Beneficios de Redis:**
- Cache persistente entre reinicios
- Compartido entre instancias (multi-replica)
- TTL automático por clave

**Configuración avanzada:**
```bash
# TTL personalizado (segundos)
EMBEDDING_CACHE_TTL=7200  # 2 horas
```

---

## Testing

### Backend Tests

```bash
# Unit tests (offline)
cd backend
pytest -m unit

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

**Test structure:**
- `__tests__/page.test.tsx` - Page component render tests
- `__tests__/error.test.tsx` - Error boundary behavior tests
- `__tests__/hooks/useRagAsk.test.tsx` - Hook logic tests (API mocking)

**Writing tests:**
- Use `@testing-library/react` for component tests
- Mock API calls with `jest.mock("@contracts/src/generated")`
- Mock `next/navigation` is pre-configured in `jest.setup.ts`

### E2E Tests (Playwright)

```bash
# Install Playwright browsers (first time only)
cd tests/e2e && pnpm install && pnpm install:browsers

# Run E2E tests
pnpm e2e

# Run with UI (interactive mode)
pnpm e2e:ui

# Debug mode
cd tests/e2e && pnpm test:debug
```

**Test files:**
- `tests/e2e/tests/health.spec.ts` - Health checks
- `tests/e2e/tests/rag-flow.spec.ts` - RAG workflow
- `tests/e2e/tests/ui.spec.ts` - Frontend UI

---

## Observability

### Starting Observability Stack

```bash
# Start with observability profile (Prometheus + Grafana)
pnpm docker:observability

# Or start everything (db + api + redis + observability)
pnpm docker:full
```

**URLs:**
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001 (admin/admin)
- Postgres Exporter: http://localhost:9187/metrics

### Logs Estructurados (JSON)

Los logs del backend son JSON con campos automáticos:

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

| Campo | Descripción |
|-------|-------------|
| `request_id` | UUID único por request (correlación) |
| `trace_id` | OpenTelemetry trace ID (si habilitado) |
| `span_id` | OpenTelemetry span ID (si habilitado) |
| `method` | HTTP method (GET, POST, etc.) |
| `path` | Request path (/v1/ask, etc.) |

**Campos de timing (RAG):**

| Campo | Descripción |
|-------|-------------|
| `embed_ms` | Tiempo de generación de embedding |
| `retrieve_ms` | Tiempo de búsqueda en DB |
| `llm_ms` | Tiempo de generación LLM |
| `total_ms` | Tiempo total del use case |

### Métricas Prometheus

Endpoint: `GET /metrics`

```bash
curl http://localhost:8000/metrics
```

**Métricas disponibles:**

| Métrica | Tipo | Descripción |
|---------|------|-------------|
| `rag_requests_total` | Counter | Total de requests por endpoint/status |
| `rag_request_latency_seconds` | Histogram | Latencia de requests |
| `rag_embed_latency_seconds` | Histogram | Latencia de embedding |
| `rag_retrieve_latency_seconds` | Histogram | Latencia de retrieval |
| `rag_llm_latency_seconds` | Histogram | Latencia de LLM |

**Ejemplo de uso con Prometheus:**

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'rag-corp'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: /metrics
```

### Tracing con OpenTelemetry (Opcional)

Para habilitar tracing distribuido:

```bash
# En .env
OTEL_ENABLED=1
```

Los traces se exportan a consola por defecto. Para producción, configurar OTLP:

```bash
OTEL_ENABLED=1
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
```

**Dependencias adicionales (instalar si usás tracing):**

```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi
```
