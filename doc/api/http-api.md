# HTTP API Documentation

**Project:** RAG Corp  
**Base URL:** `http://localhost:8000`  
**API Prefix:** `/v1` or `/api/v1`  
**Version:** 0.1.0  
**Last Updated:** 2026-01-13

---

## Interactive Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

> OpenAPI se exporta desde el backend (`pnpm contracts:export`).

---

## Authentication + RBAC

- Header requerido cuando hay auth: `X-API-Key`.
- Auth deshabilitada cuando `API_KEYS_CONFIG` y `RBAC_CONFIG` estan vacias.
- RBAC usa permisos con fallback a scopes legacy.

### API_KEYS_CONFIG (scopes)

```bash
API_KEYS_CONFIG='{"prod-ingest-key":["ingest"],"prod-query-key":["ask"],"admin-key":["ingest","ask","metrics"]}'
```

Scopes soportados:

| Scope | Permisos (RBAC) | Endpoints |
|-------|------------------|-----------|
| `ingest` | `documents:create`, `documents:read`, `documents:delete` | `/v1/ingest/*`, `/v1/documents*` |
| `ask` | `documents:read`, `query:search`, `query:ask`, `query:stream` | `/v1/query`, `/v1/ask`, `/v1/ask/stream`, `/v1/documents*` |
| `metrics` | `admin:metrics` | `/metrics` |
| `*` | `*` | Todo |

### RBAC_CONFIG (roles + key hashes)

```bash
RBAC_CONFIG='{
  "roles": {
    "analyst": {
      "permissions": ["documents:read", "query:search", "query:ask"],
      "inherits_from": "readonly"
    }
  },
  "key_roles": {
    "abc123hash...": "admin",
    "def456hash...": "user"
  }
}'
```

> Los hashes son `sha256(api_key)[:12]`. Ver `backend/app/rbac.py`.

### Metrics auth

`/metrics` requiere auth solo cuando `METRICS_REQUIRE_AUTH=true`.

---

## Rate Limiting

Token bucket por API key (o IP cuando auth esta deshabilitada).

```bash
RATE_LIMIT_RPS=10
RATE_LIMIT_BURST=20
```

Headers cuando aplica:
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `Retry-After` (solo en 429)

---

## Error Responses (RFC 7807)

Todas las respuestas de error usan Problem Details.

```json
{
  "type": "https://api.ragcorp.local/errors/forbidden",
  "title": "Forbidden",
  "status": 403,
  "detail": "Invalid API key.",
  "code": "FORBIDDEN",
  "instance": "http://localhost:8000/v1/ask"
}
```

---

## Endpoints

### Health Check

`GET /healthz`

Params:
- `full` (bool, default false): incluye chequeo Google API

```bash
curl http://localhost:8000/healthz
curl "http://localhost:8000/healthz?full=true"
```

### Metrics

`GET /metrics`

```bash
curl http://localhost:8000/metrics
```

Si `METRICS_REQUIRE_AUTH=true`, requiere `X-API-Key` con scope `metrics` o permiso `admin:metrics`.

### Ingest Text

`POST /v1/ingest/text`

```bash
curl -X POST http://localhost:8000/v1/ingest/text \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"title":"Doc","text":"Contenido...","source":"https://...","metadata":{"team":"docs"}}'
```

Response:

```json
{"document_id":"...","chunks":5}
```

### Ingest Batch

`POST /v1/ingest/batch`

```bash
curl -X POST http://localhost:8000/v1/ingest/batch \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"documents":[{"title":"Doc","text":"Contenido"}]}'
```

Response:

```json
{"documents":[{"document_id":"...","chunks":5}],"total_chunks":5}
```

### Documents List

`GET /v1/documents?limit=50&offset=0`

```bash
curl -H "X-API-Key: your-key" http://localhost:8000/v1/documents
```

Response:

```json
{
  "documents": [
    {"id":"...","title":"Doc","source":null,"metadata":{},"created_at":"..."}
  ]
}
```

### Document Detail

`GET /v1/documents/{document_id}`

```bash
curl -H "X-API-Key: your-key" http://localhost:8000/v1/documents/UUID
```

Response:

```json
{
  "id":"...",
  "title":"Doc",
  "source":null,
  "metadata":{},
  "created_at":"...",
  "deleted_at":null
}
```

### Document Delete

`DELETE /v1/documents/{document_id}`

```bash
curl -X DELETE -H "X-API-Key: your-key" http://localhost:8000/v1/documents/UUID
```

Response:

```json
{"deleted":true}
```

### Query Documents

`POST /v1/query`

Body:
- `query` (string, required)
- `top_k` (int, default 5)
- `use_mmr` (bool, default false)

Response:

```json
{
  "matches": [
    {"chunk_id":"...","document_id":"...","content":"...","score":0.83}
  ]
}
```

### Ask (RAG)

`POST /v1/ask`

Body:
- `query` (string, required)
- `top_k` (int, default 5)
- `use_mmr` (bool, default false)
- `conversation_id` (string, optional)

Response:

```json
{"answer":"...","sources":["..."],"conversation_id":"..."}
```

### Ask (Streaming)

`POST /v1/ask/stream`

Body igual a `/v1/ask`. Respuesta SSE (`text/event-stream`).

Eventos:
- `sources`: `{ "sources": [{"chunk_id":"...","content":"..."}], "conversation_id":"..." }`
- `token`: `{ "token": "..." }`
- `done`: `{ "answer": "...", "conversation_id": "..." }`
- `error`: `{ "error": "..." }`

Ejemplo (fetch):

```ts
const res = await fetch("/v1/ask/stream", {
  method: "POST",
  headers: { "Content-Type": "application/json", "X-API-Key": "your-key" },
  body: JSON.stringify({ query: "Que es RAG?", top_k: 3 })
});
```
