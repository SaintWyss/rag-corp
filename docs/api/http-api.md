# HTTP API Documentation (v6)

**Project:** RAG Corp
**Base URL:** `http://localhost:8000`
**API Prefix:** `/v1` (canonical) + `/api/v1` (alias)
**Last Updated:** 2026-01-22

---

## Interactive Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: `shared/contracts/openapi.json`

Regenerar contratos:

```bash
pnpm contracts:export
pnpm contracts:gen
```

---

## Authentication + Authorization

Los endpoints `/v1/*` aceptan **JWT (usuarios)** o **X-API-Key (servicios)**.
Los endpoints `/auth/*` son para JWT.

### JWT (UI)

- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/logout`

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"<ADMIN_EMAIL>","password":"<ADMIN_PASSWORD>"}'
```

### API keys (service auth)

- Header: `X-API-Key`
- Auth deshabilitada si `API_KEYS_CONFIG` y `RBAC_CONFIG` estan vacias
- RBAC aplica solo a API keys (ver `docs/api/rbac.md`)

Scopes legacy:

| Scope | Endpoints |
|-------|-----------|
| `ingest` | `/v1/workspaces/{workspace_id}/documents*`, `/v1/workspaces/{workspace_id}/ingest/*` |
| `ask` | `/v1/workspaces/{workspace_id}/query`, `/v1/workspaces/{workspace_id}/ask*` |
| `metrics` | `/metrics` |
| `*` | Todo |

### Metrics auth

`/metrics` requiere auth solo si `METRICS_REQUIRE_AUTH=true`.

---

## Error Responses (RFC 7807)

Todas las respuestas de error usan Problem Details (`application/problem+json`).

```json
{
  "type": "https://api.ragcorp.local/errors/forbidden",
  "title": "Forbidden",
  "status": 403,
  "detail": "Invalid API key.",
  "code": "FORBIDDEN",
  "instance": "http://localhost:8000/v1/workspaces"
}
```

---

## Workspace-first flow (v6)

```bash
API_KEY="<API_KEY>"

# 1) Crear workspace
curl -X POST http://localhost:8000/v1/workspaces \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{"name":"Workspace Demo","visibility":"PRIVATE"}'

WORKSPACE_ID="<WORKSPACE_ID>"

# 2) Upload async
curl -X POST http://localhost:8000/v1/workspaces/${WORKSPACE_ID}/documents/upload \
  -H "X-API-Key: ${API_KEY}" \
  -F "file=@/path/to/file.pdf" \
  -F "title=Documento demo"

# 3) Poll hasta READY
curl -H "X-API-Key: ${API_KEY}" \
  "http://localhost:8000/v1/workspaces/${WORKSPACE_ID}/documents?status=READY"

# 4) Ask scoped
curl -X POST http://localhost:8000/v1/workspaces/${WORKSPACE_ID}/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{"query":"Que dice el documento?","top_k":3}'
```

---

## Endpoints

### Health / Readiness / Metrics

- `GET /healthz`
- `GET /readyz`
- `GET /metrics`

### Auth (JWT)

- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/logout`

### Admin (JWT admin o API key con `admin:config` via RBAC)

- `GET /auth/users`
- `POST /auth/users`
- `POST /auth/users/{user_id}/disable`
- `POST /auth/users/{user_id}/reset-password`
- `GET /v1/admin/audit`

### Workspaces

- `GET /v1/workspaces`
- `POST /v1/workspaces`
- `GET /v1/workspaces/{workspace_id}`
- `PATCH /v1/workspaces/{workspace_id}`
- `POST /v1/workspaces/{workspace_id}/publish`
- `POST /v1/workspaces/{workspace_id}/share`
- `POST /v1/workspaces/{workspace_id}/archive`

### Documents (scoped)

- `GET /v1/workspaces/{workspace_id}/documents`
- `GET /v1/workspaces/{workspace_id}/documents/{document_id}`
- `DELETE /v1/workspaces/{workspace_id}/documents/{document_id}`
- `POST /v1/workspaces/{workspace_id}/documents/upload`
- `POST /v1/workspaces/{workspace_id}/documents/{document_id}/reprocess`

### Ingest (scoped)

- `POST /v1/workspaces/{workspace_id}/ingest/text`
- `POST /v1/workspaces/{workspace_id}/ingest/batch`

### Query / Ask (scoped)

- `POST /v1/workspaces/{workspace_id}/query`
- `POST /v1/workspaces/{workspace_id}/ask`
- `POST /v1/workspaces/{workspace_id}/ask/stream`

---

## Legacy endpoints (DEPRECATED)

Los endpoints legacy se mantienen por compatibilidad pero **requieren** `workspace_id` (query param).
Si falta, el backend responde con error de validacion.

### Documents (legacy)

- `GET /v1/documents?workspace_id=...`
- `POST /v1/documents/upload?workspace_id=...`
- `DELETE /v1/documents/{document_id}?workspace_id=...`
- `POST /v1/documents/{document_id}/reprocess?workspace_id=...`

### Query / Ask (legacy)

- `POST /v1/query?workspace_id=...`
- `POST /v1/ask?workspace_id=...`
- `POST /v1/ask/stream?workspace_id=...`

### Ingest (legacy)

- `POST /v1/ingest/text?workspace_id=...`
- `POST /v1/ingest/batch?workspace_id=...`

