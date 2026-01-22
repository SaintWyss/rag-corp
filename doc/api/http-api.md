# HTTP API Documentation

**Project:** RAG Corp  
**Base URL:** `http://localhost:8000`  
**API Prefix:** `/v1` (canonical; `/api/v1` alias legacy)  
**Frontend Proxy:** `/api/*` -> `/v1/*`, `/auth/*` -> `/auth/*`  
**Version:** 0.1.0  
**Last Updated:** 2026-01-21

---

## Interactive Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

> OpenAPI se exporta desde el backend (`pnpm contracts:export`).

## Regenerar contratos (OpenAPI + cliente)

```bash
pnpm contracts:export
pnpm contracts:gen
```

Genera `shared/contracts/openapi.json` y `shared/contracts/src/generated.ts`.

---

## Authentication + Authorization

Los endpoints `/v1/*` aceptan **JWT (usuarios)** o **X-API-Key (servicios)**.  
Los endpoints `/auth/*` son para JWT y gestion de usuarios. `/metrics` usa API key si requiere auth.

### JWT (UI)

- Login: `POST /auth/login`
- Current user: `GET /auth/me`
- Logout: `POST /auth/logout`

El login responde con `access_token` (Bearer) y setea cookie httpOnly (`access_token` por defecto; configurable con `JWT_COOKIE_NAME`).

Ejemplo:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"<ADMIN_EMAIL>","password":"<ADMIN_PASSWORD>"}'
```

Usar token:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/auth/me
```

### API keys (service auth)

- Header requerido cuando hay auth: `X-API-Key`.
- Auth deshabilitada cuando `API_KEYS_CONFIG` y `RBAC_CONFIG` estan vacias.
- RBAC usa permisos con fallback a scopes legacy.

#### API_KEYS_CONFIG (scopes)

```bash
API_KEYS_CONFIG='{"<INGEST_KEY>":["ingest"],"<QUERY_KEY>":["ask"],"<ADMIN_KEY>":["ingest","ask","metrics"]}'
```

Scopes soportados:

| Scope | Permisos (RBAC) | Endpoints |
|-------|------------------|-----------|
| `ingest` | `documents:create`, `documents:read`, `documents:delete` | `/v1/ingest/*`, `/v1/documents*` |
| `ask` | `documents:read`, `query:search`, `query:ask`, `query:stream` | `/v1/query`, `/v1/ask`, `/v1/ask/stream`, `/v1/documents*` |
| `metrics` | `admin:metrics` | `/metrics` |
| `*` | `*` | Todo |

#### RBAC_CONFIG (roles + key hashes)

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

#### Admin config con API key

Para llamar endpoints `/auth/users*` con API key se requiere RBAC (permiso `admin:config`), porque no hay scope legacy equivalente.

### Metrics auth

`/metrics` requiere auth solo cuando `METRICS_REQUIRE_AUTH=true` (API key con `admin:metrics`).

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
- `full` (bool, default false): incluye chequeo Google API (si `HEALTHCHECK_GOOGLE_ENABLED=true`)

```bash
curl http://localhost:8000/healthz
curl "http://localhost:8000/healthz?full=true"
```

### Readiness

`GET /readyz`

```bash
curl http://localhost:8000/readyz
```

### Metrics

`GET /metrics`

```bash
curl http://localhost:8000/metrics
```

Si `METRICS_REQUIRE_AUTH=true`, requiere `X-API-Key` con scope `metrics` o permiso `admin:metrics`.

---

## Auth (JWT)

### Login

`POST /auth/login`

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"<ADMIN_EMAIL>","password":"<ADMIN_PASSWORD>"}'
```

Response:

```json
{"access_token":"...","expires_in":1800,"user":{"id":"...","email":"...","role":"admin","is_active":true,"created_at":"..."}}
```

### Me

`GET /auth/me`

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/auth/me
```

### Logout

`POST /auth/logout`

```bash
curl -X POST http://localhost:8000/auth/logout
```

---

## Admin Users (admin-only)

Requiere JWT admin o API key con permiso `admin:config` (via RBAC).

### List Users

`GET /auth/users`

### Create User

`POST /auth/users`

Body: `email`, `password`, `role` (`admin|employee`)

### Disable User

`POST /auth/users/{user_id}/disable`

### Reset Password

`POST /auth/users/{user_id}/reset-password`

Body: `password`

---

## Workspaces (v4)

Visibilidad:
- `PRIVATE`
- `ORG_READ`
- `SHARED`

### List

`GET /v1/workspaces`

Query params:
- `owner_user_id` (UUID, opcional)
- `include_archived` (bool, default false)

```bash
curl -H "X-API-Key: <API_KEY>" http://localhost:8000/v1/workspaces
```

### Create

`POST /v1/workspaces`

```bash
curl -X POST http://localhost:8000/v1/workspaces \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <API_KEY>" \
  -d '{"name":"Workspace Demo","visibility":"PRIVATE"}'
```

### Detail / Update

`GET /v1/workspaces/{workspace_id}`  
`PATCH /v1/workspaces/{workspace_id}`

### Publish / Share / Archive (owner/admin)

`POST /v1/workspaces/{workspace_id}/publish`  
`POST /v1/workspaces/{workspace_id}/share`  
`POST /v1/workspaces/{workspace_id}/archive`

Payload para share:

```json
{"user_ids":["<USER_ID>"]}
```

---

## Ingest (admin-only, scoped)

### Ingest Text

`POST /v1/workspaces/{workspace_id}/ingest/text`

```bash
curl -X POST http://localhost:8000/v1/workspaces/<WORKSPACE_ID>/ingest/text \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <API_KEY>" \
  -d '{"title":"Doc","text":"Contenido...","source":"https://...","metadata":{"team":"docs"}}'
```

Response:

```json
{"document_id":"...","chunks":5}
```

### Ingest Batch

`POST /v1/workspaces/{workspace_id}/ingest/batch`

```bash
curl -X POST http://localhost:8000/v1/workspaces/<WORKSPACE_ID>/ingest/batch \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <API_KEY>" \
  -d '{"documents":[{"title":"Doc","text":"Contenido"}]}'
```

Response:

```json
{"documents":[{"document_id":"...","chunks":5}],"total_chunks":5}
```

---

## Documents (scoped)

### List

`GET /v1/workspaces/{workspace_id}/documents`

Query params:
- `q`: texto libre (busca en title/source/file_name/metadata)
- `status`: `PENDING|PROCESSING|READY|FAILED`
- `tag`: filtro por tag
- `sort`: `created_at_desc|created_at_asc|title_asc|title_desc`
- `cursor` o `offset`: paginacion
- `limit` (1-200)

```bash
curl -H "X-API-Key: <API_KEY>" \
  "http://localhost:8000/v1/workspaces/<WORKSPACE_ID>/documents?status=READY"
```

Response:

```json
{
  "documents": [
    {"id":"...","title":"Doc","source":null,"metadata":{},"created_at":"...","file_name":null,"mime_type":null,"status":"READY","tags":[]}
  ],
  "next_cursor":"..."
}
```

ACL:
- JWT employee ve solo documentos propios o con `allowed_roles` compatibles.
- API keys mantienen el comportamiento actual (sin filtro por ACL).

### Detail

`GET /v1/workspaces/{workspace_id}/documents/{document_id}`

```bash
curl -H "X-API-Key: <API_KEY>" \
  http://localhost:8000/v1/workspaces/<WORKSPACE_ID>/documents/<DOCUMENT_ID>
```

Response:

```json
{
  "id":"...",
  "title":"Doc",
  "source":null,
  "metadata":{},
  "created_at":"...",
  "deleted_at":null,
  "file_name":"report.pdf",
  "mime_type":"application/pdf",
  "status":"READY",
  "error_message":null,
  "tags":[]
}
```

### Delete (admin-only)

`DELETE /v1/workspaces/{workspace_id}/documents/{document_id}`

```bash
curl -X DELETE -H "X-API-Key: <API_KEY>" \
  http://localhost:8000/v1/workspaces/<WORKSPACE_ID>/documents/<DOCUMENT_ID>
```

Response:

```json
{"deleted":true}
```

### Upload (admin-only, async)

`POST /v1/workspaces/{workspace_id}/documents/upload` (multipart)

Campos:
- `file` (required)
- `title` (optional)
- `source` (optional)
- `metadata` (optional JSON string; soporta `tags` y `allowed_roles`)

Validaciones:
- MIME allowlist: `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- Tamaño maximo: `MAX_UPLOAD_BYTES`

Response:

```json
{"document_id":"...","status":"PENDING","file_name":"...","mime_type":"application/pdf"}
```

### Reprocess (admin-only)

`POST /v1/workspaces/{workspace_id}/documents/{document_id}/reprocess`

Respuesta 202 si se encola. Si esta en PROCESSING devuelve 409.

---

## Query / Ask

### Query Documents

`POST /v1/workspaces/{workspace_id}/query`

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

`POST /v1/workspaces/{workspace_id}/ask`

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

`POST /v1/workspaces/{workspace_id}/ask/stream`

Body igual a `/v1/ask`. Respuesta SSE (`text/event-stream`).

Eventos:
- `sources`: `{ "sources": [{"chunk_id":"...","content":"..."}], "conversation_id":"..." }`
- `token`: `{ "token": "..." }`
- `done`: `{ "answer": "...", "conversation_id": "..." }`
- `error`: `{ "error": "..." }`

Ejemplo (fetch):

```ts
const res = await fetch("/v1/workspaces/<WORKSPACE_ID>/ask/stream", {
  method: "POST",
  headers: { "Content-Type": "application/json", "X-API-Key": "<API_KEY>" },
  body: JSON.stringify({ query: "Que es RAG?", top_k: 3 })
});
```

---

## Legacy endpoints (deprecated)

Los endpoints legacy se mantienen por compatibilidad pero **requieren** `workspace_id`.
Se recomienda migrar a las rutas nested.

### Documents (legacy)

`GET /v1/documents?workspace_id=...`  
`POST /v1/documents/upload?workspace_id=...`  
`DELETE /v1/documents/{document_id}?workspace_id=...`  
`POST /v1/documents/{document_id}/reprocess?workspace_id=...`

### Query / Ask (legacy)

`POST /v1/query?workspace_id=...`  
`POST /v1/ask?workspace_id=...`  
`POST /v1/ask/stream?workspace_id=...`

### Ingest (legacy)

`POST /v1/ingest/text?workspace_id=...`  
`POST /v1/ingest/batch?workspace_id=...`
