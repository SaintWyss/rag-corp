# HTTP API Documentation — RAG Corp v6

**Project:** RAG Corp  
**Base URL:** `http://localhost:8000`  
**API Prefix:** `/v1` (canonical) + `/api/v1` (alias)  
**Last Updated:** 2026-01-24  
**Source of Truth:** `shared/contracts/openapi.json`

---

## TL;DR

RAG Corp expone una API REST con autenticación dual (JWT para UI, API Keys para integraciones). Todas las operaciones de documentos y RAG están scoped por `workspace_id`.

---

## Interactive Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** `shared/contracts/openapi.json`

**Regenerar contratos:**

```bash
pnpm contracts:export
pnpm contracts:gen
```

---

## Authentication + Authorization

RAG Corp soporta dos mecanismos de autenticación:

### 1. JWT (Para UI / Usuarios Humanos)

Autenticación basada en cookies httpOnly. Ideal para el frontend.

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/auth/login` | POST | Login con email/password |
| `/auth/me` | GET | Usuario actual |
| `/auth/logout` | POST | Cerrar sesión |

**Ejemplo completo:**

```bash
# 1. Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"secret123"}' \
  -c cookies.txt

# 2. Usar sesión
curl http://localhost:8000/auth/me -b cookies.txt

# 3. Logout
curl -X POST http://localhost:8000/auth/logout -b cookies.txt
```

**Cookies emitidas:**
- `access_token`: JWT token (httpOnly, Secure en prod)
- `SameSite`: Lax (configurable)

### 2. API Keys (Para Integraciones / CI)

Autenticación via header `X-API-Key`. Ideal para scripts, CI/CD, e integraciones.

**Header:** `X-API-Key: <your-api-key>`

**Configuración:**

```bash
# En .env
API_KEYS_CONFIG='[{"key":"sk-test-123","name":"ci-bot","scopes":["ingest","ask"]}]'
RBAC_CONFIG='{"ingest":["documents:*"],"ask":["query:*","ask:*"]}'
```

#### Scopes disponibles

| Scope | Endpoints |
|-------|-----------|
| `ingest` | `/v1/workspaces/{ws_id}/documents/*`, `/v1/workspaces/{ws_id}/ingest/*` |
| `ask` | `/v1/workspaces/{ws_id}/query`, `/v1/workspaces/{ws_id}/ask/*` |
| `metrics` | `/metrics` |
| `admin:*` | Todos los endpoints admin |
| `*` | Acceso total |

#### Ejemplo con API Key

```bash
API_KEY="sk-test-123"

curl http://localhost:8000/v1/workspaces \
  -H "X-API-Key: ${API_KEY}"
```

#### Diferencias entre JWT y API Key

| Aspecto | JWT (Cookies) | API Key |
|---------|---------------|---------|
| Uso típico | UI/Browser | Scripts/CI |
| Expiración | ~24h | Sin expiración |
| Rotación | Automática | Manual |
| Auditoría actor | `user:<uuid>` | `service:<hash>` |
| RBAC | Basado en rol (admin/employee) | Basado en scopes |

#### Seguridad de API Keys

⚠️ **Nunca usar API Keys en frontend público.** Son para:
- CI/CD pipelines
- Integraciones server-to-server
- Scripts de administración

Para generar/rotar keys:
1. Actualizar `API_KEYS_CONFIG` en variables de entorno
2. Restart del backend

---

## Error Responses (RFC 7807)

Todas las respuestas de error usan Problem Details (`application/problem+json`).

```json
{
  "type": "https://api.ragcorp.local/errors/forbidden",
  "title": "Forbidden",
  "status": 403,
  "detail": "You don't have access to this workspace.",
  "code": "FORBIDDEN",
  "instance": "/v1/workspaces/123/documents"
}
```

### Códigos de error comunes

| Status | Code | Descripción |
|--------|------|-------------|
| 400 | `VALIDATION_ERROR` | Request inválido |
| 401 | `UNAUTHORIZED` | Sin autenticación |
| 403 | `FORBIDDEN` | Sin permisos |
| 404 | `NOT_FOUND` | Recurso no existe |
| 409 | `CONFLICT` | Conflicto (ej: nombre duplicado) |
| 413 | `PAYLOAD_TOO_LARGE` | Archivo muy grande |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | MIME no soportado |
| 429 | `RATE_LIMITED` | Demasiadas requests |

---

## Complete Workflow Example

Flujo completo: Login → Crear Workspace → Upload → Poll → Ask

```bash
# Variables
API_KEY="sk-test-123"
BASE_URL="http://localhost:8000"

# 1. Crear workspace
WORKSPACE=$(curl -s -X POST ${BASE_URL}/v1/workspaces \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{"name":"Mi Proyecto","visibility":"PRIVATE"}')

WORKSPACE_ID=$(echo $WORKSPACE | jq -r '.id')
echo "Created workspace: ${WORKSPACE_ID}"

# 2. Upload documento
UPLOAD=$(curl -s -X POST ${BASE_URL}/v1/workspaces/${WORKSPACE_ID}/documents/upload \
  -H "X-API-Key: ${API_KEY}" \
  -F "file=@documento.pdf" \
  -F "title=Manual de Usuario")

DOC_ID=$(echo $UPLOAD | jq -r '.id')
echo "Uploaded document: ${DOC_ID} (status: $(echo $UPLOAD | jq -r '.status'))"

# 3. Poll hasta READY (máx 60 segundos)
for i in {1..12}; do
  STATUS=$(curl -s ${BASE_URL}/v1/workspaces/${WORKSPACE_ID}/documents/${DOC_ID} \
    -H "X-API-Key: ${API_KEY}" | jq -r '.status')
  echo "Status: ${STATUS}"
  if [ "$STATUS" = "READY" ]; then break; fi
  if [ "$STATUS" = "FAILED" ]; then echo "Processing failed!"; exit 1; fi
  sleep 5
done

# 4. Ask question
ANSWER=$(curl -s -X POST ${BASE_URL}/v1/workspaces/${WORKSPACE_ID}/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{"query":"¿Qué dice el documento?","top_k":3}')

echo "Answer: $(echo $ANSWER | jq -r '.answer')"
echo "Sources: $(echo $ANSWER | jq -r '.sources')"
```

---

## Endpoints Reference

### Health / Metrics

| Endpoint | Método | Auth | Descripción |
|----------|--------|------|-------------|
| `/healthz` | GET | No | Liveness check |
| `/readyz` | GET | No | Readiness check |
| `/metrics` | GET | Condicional* | Prometheus metrics |

*`METRICS_REQUIRE_AUTH=true` requiere API Key con scope `metrics`.

### Auth (JWT)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/auth/login` | POST | Login |
| `/auth/me` | GET | Usuario actual |
| `/auth/logout` | POST | Cerrar sesión |

### Admin (JWT admin o API Key con `admin:config`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/auth/users` | GET | Listar usuarios |
| `/auth/users` | POST | Crear usuario |
| `/auth/users/{user_id}/disable` | POST | Deshabilitar usuario |
| `/auth/users/{user_id}/reset-password` | POST | Reset password |
| `/v1/admin/audit` | GET | Consultar auditoría |

### Workspaces

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/v1/workspaces` | GET | Listar workspaces visibles |
| `/v1/workspaces` | POST | Crear workspace |
| `/v1/workspaces/{workspace_id}` | GET | Obtener workspace |
| `/v1/workspaces/{workspace_id}` | PATCH | Actualizar workspace |
| `/v1/workspaces/{workspace_id}/publish` | POST | Publicar (ORG_READ) |
| `/v1/workspaces/{workspace_id}/share` | POST | Compartir (SHARED + ACL) |
| `/v1/workspaces/{workspace_id}/archive` | POST | Archivar |

### Documents (Scoped)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/v1/workspaces/{ws_id}/documents` | GET | Listar documentos |
| `/v1/workspaces/{ws_id}/documents/{doc_id}` | GET | Obtener documento |
| `/v1/workspaces/{ws_id}/documents/{doc_id}` | DELETE | Eliminar documento |
| `/v1/workspaces/{ws_id}/documents/upload` | POST | Upload async |
| `/v1/workspaces/{ws_id}/documents/{doc_id}/reprocess` | POST | Reprocesar |

### Ingest (Scoped)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/v1/workspaces/{ws_id}/ingest/text` | POST | Ingest texto directo |
| `/v1/workspaces/{ws_id}/ingest/batch` | POST | Ingest batch |

### Query / Ask (Scoped)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/v1/workspaces/{ws_id}/query` | POST | Solo retrieval |
| `/v1/workspaces/{ws_id}/ask` | POST | RAG completo |
| `/v1/workspaces/{ws_id}/ask/stream` | POST | RAG streaming (SSE) |

---

## Legacy Endpoints (DEPRECATED)

Estos endpoints se mantienen para compatibilidad pero **requieren** `workspace_id` como query param.

```bash
# Legacy (deprecated)
curl "/v1/documents?workspace_id=abc-123"

# Canonical (preferred)
curl "/v1/workspaces/abc-123/documents"
```

| Legacy | Canonical |
|--------|-----------|
| `/v1/documents?workspace_id=...` | `/v1/workspaces/{ws_id}/documents` |
| `/v1/ask?workspace_id=...` | `/v1/workspaces/{ws_id}/ask` |
| `/v1/query?workspace_id=...` | `/v1/workspaces/{ws_id}/query` |
| `/v1/ingest/text?workspace_id=...` | `/v1/workspaces/{ws_id}/ingest/text` |

**Removal target:** v8

---

## Upload Limits

| Límite | Valor | Evidencia |
|--------|-------|-----------|
| Max body size | 10 MB | `apps/backend/app/crosscutting/config.py:107` |
| MIME types soportados | PDF, DOCX, TXT | Validación en upload handler |

---

## References

- OpenAPI spec: `shared/contracts/openapi.json`
- RBAC docs: `docs/api/rbac.md`
- Frontend API client: `apps/frontend/src/shared/api/`
