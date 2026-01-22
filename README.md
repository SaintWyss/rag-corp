# RAG Corp

Sistema de **Retrieval-Augmented Generation** (RAG) empresarial que permite ingestar documentos, buscarlos semánticamente y obtener respuestas contextuales generadas por LLM. Resuelve el problema de documentación dispersa: consultas en lenguaje natural con respuestas precisas y fuentes citadas, sin enviar documentos completos a APIs externas.

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)

---

## Features

- ✅ Workspaces v4 (visibilidad + ACL) (`/v1/workspaces`)
- ✅ Documentos scoped por workspace (`/v1/workspaces/{id}/documents/*`, estados PENDING/PROCESSING/READY/FAILED)
- ✅ Query/Ask scoped (`/v1/workspaces/{id}/query`, `/ask`, `/ask/stream`)
- ✅ Legacy endpoints soportados y deprecated (`/v1/documents`, `/v1/ask`; `workspace_id` requerido)
- ✅ Busqueda vectorial con PostgreSQL + pgvector (indice IVFFlat)
- ✅ RAG con Gemini 1.5 Flash y prompts versionados
- ✅ Chat streaming SSE con multi-turn (`/v1/workspaces/{id}/ask/stream`, `conversation_id`)
- ✅ Cache de embeddings (memory por defecto, Redis opcional)
- ✅ UI en Next.js (Workspaces, Documents, Chat)
- ✅ Auth dual: JWT (admin/employee) + API keys (CI/E2E)
- ✅ Storage S3/MinIO + worker Redis (procesamiento en background)
- ✅ Contratos tipados (OpenAPI -> TypeScript via Orval)
- ✅ Clean Architecture (Domain/Application/Infrastructure)
- ✅ Seguridad: API keys + scopes, RBAC por permisos, rate limiting
- ✅ Observabilidad: /healthz, /readyz, /metrics, logs JSON

---

## Arquitectura

### Componentes

| Componente | Tecnología | Ubicación |
|------------|------------|-----------|
| **Backend** | FastAPI + Python 3.11 | `backend/` |
| **Base de Datos** | PostgreSQL 16 + pgvector 0.8.1 | `infra/postgres/` |
| **Frontend** | Next.js 16 + TypeScript | `frontend/` |
| **Contracts** | OpenAPI 3.1 + Orval | `shared/contracts/` |
| **Embeddings/LLM** | Google Gemini API | Servicios externos |
| **Cache** | In-memory / Redis | `backend/app/infrastructure/cache.py` |
| **Worker** | RQ + Redis | `backend/app/worker.py` |
| **Storage** | S3/MinIO | `backend/app/infrastructure/storage/` |
| **Observability** | Prometheus + Grafana | `infra/` (profile observability) |

### Flujo "Ask" (consulta RAG)

```
1. Usuario envía query → Frontend (useRagAsk hook)
2. Frontend llama POST /v1/workspaces/{id}/ask → Backend (routes.py)
3. AnswerQueryUseCase embebe la query → GoogleEmbeddingService
4. Búsqueda vectorial top-k (scoped por workspace) → PostgresDocumentRepository
5. ContextBuilder arma contexto con chunks recuperados
6. GoogleLLMService genera respuesta grounded en contexto
7. Response con answer + sources → Usuario
```

### Flujo "Chat streaming" (multi-turn)

```
1. Usuario envia query → /v1/workspaces/{id}/ask/stream con conversation_id opcional
2. Backend recupera historial (in-memory) y arma llm_query
3. Se emite evento "sources" + tokens SSE
4. "done" incluye answer y conversation_id
5. UI muestra burbujas y guarda el ID para el siguiente turno
```

### Flujo "Ingest" (ingesta de documentos)

```
1. Cliente envía documento → POST /v1/workspaces/{id}/ingest/text
2. IngestDocumentUseCase valida y chunkea → SimpleTextChunker
3. GoogleEmbeddingService genera embeddings por chunk
4. PostgresDocumentRepository guarda documento + chunks (transacción atómica)
5. Response con document_id + chunks_created → Cliente
```

### Flujo "Upload" (async con worker)

```
1. Admin sube archivo → POST /v1/workspaces/{id}/documents/upload (multipart)
2. API guarda binario en S3/MinIO y metadata en Postgres (status=PENDING)
3. Worker (RQ) procesa en background → PROCESSING → READY/FAILED
4. UI Documents muestra estado + permite reprocess
```

---

## Stack

| Capa | Tecnología |
|------|------------|
| API | FastAPI, Pydantic, psycopg 3.2 |
| DB | PostgreSQL 16, pgvector 0.8.1 |
| Queue/Cache | Redis 7 (RQ + cache opcional) |
| Storage | S3 compatible (MinIO en dev) |
| AI | Google Gemini (text-embedding-004, Gemini 1.5 Flash) |
| Frontend | Next.js 16, TypeScript 5, Tailwind CSS 4 |
| Contracts | OpenAPI 3.1, Orval |
| DevOps | Docker Compose, pnpm, Turbo |

---

## Quickstart Local

### Requisitos

- Docker + Docker Compose
- Node.js 20.9+ y pnpm 10+
- Cuenta Google Cloud con Gemini API habilitada (opcional si usas FAKE_LLM/FAKE_EMBEDDINGS)

### Variables de Entorno

```bash
cp .env.example .env
```

Editar `.env` con valores minimos:

| Variable | Descripción | Requerida |
|----------|-------------|-----------|
| `GOOGLE_API_KEY` | API key de Google Gemini | ✅ (si no usas FAKE_*) |
| `FAKE_LLM` | Usa Fake LLM (1 = on) | Opcional |
| `FAKE_EMBEDDINGS` | Usa Fake embeddings (1 = on) | Opcional |
| `DATABASE_URL` | Connection string PostgreSQL | Requerida si corres backend local |
| `API_KEYS_CONFIG` | JSON con API keys y scopes | Opcional (si vacio, auth off) |
| `RBAC_CONFIG` | JSON con roles y key hashes | Opcional |
| `REDIS_URL` | Redis para worker/cache | Opcional |
| `S3_ENDPOINT_URL` | Endpoint S3/MinIO | Opcional (requerido para upload) |
| `S3_BUCKET` | Bucket S3/MinIO | Opcional |
| `S3_ACCESS_KEY` | Access key S3/MinIO | Opcional |
| `S3_SECRET_KEY` | Secret key S3/MinIO | Opcional |

### Levantar Servicios

```bash
# Instalar dependencias
pnpm install

# Levantar PostgreSQL (db) + Backend (rag-api)
pnpm docker:up

# Esperar ~30s y verificar
docker compose ps
```

### Full Stack (storage + worker)

```bash
# 1) Configurar storage para MinIO (compose)
export S3_ENDPOINT_URL=http://minio:9000
export S3_BUCKET=<S3_BUCKET>
export S3_ACCESS_KEY=<S3_ACCESS_KEY>
export S3_SECRET_KEY=<S3_SECRET_KEY>

# 2) Levantar stack completo
pnpm stack:full

# 3) Migraciones
pnpm db:migrate

# 4) Crear admin (idempotente)
pnpm admin:bootstrap -- --email "<ADMIN_EMAIL>" --password "<ADMIN_PASSWORD>"
```

> Si corres el backend fuera de Docker, usa `S3_ENDPOINT_URL=http://localhost:9000`.

### Generar Contratos

```bash
pnpm contracts:export
pnpm contracts:gen
```

### Ejecutar en Desarrollo

```bash
# Frontend (dev server)
pnpm dev

# Backend (si queres correrlo local sin Docker)
# cd backend
# alembic upgrade head
# uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Verificar Funcionamiento

```bash
# Health check
curl http://localhost:8000/healthz
# Esperado: {"ok":true,"db":"connected","request_id":"..."}

# API readiness (dep core)
curl http://localhost:8000/readyz

# Worker readiness (solo con perfil worker/full)
curl http://localhost:8001/readyz

# Métricas (si METRICS_REQUIRE_AUTH=false)
curl http://localhost:8000/metrics | head -5

# Login JWT (UI / auth)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"<ADMIN_EMAIL>","password":"<ADMIN_PASSWORD>"}'

# Workspace v4 (scoped)
API_KEY="<API_KEY>"

# Crear workspace (toma workspace_id del response)
curl -X POST http://localhost:8000/v1/workspaces \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{"name":"Workspace Demo","visibility":"PRIVATE"}'

WORKSPACE_ID="<WORKSPACE_ID>"

# Subir documento (async)
curl -X POST http://localhost:8000/v1/workspaces/${WORKSPACE_ID}/documents/upload \
  -H "X-API-Key: ${API_KEY}" \
  -F "file=@/path/to/file.pdf" \
  -F "title=Documento demo"

# Listar documentos del workspace
curl -H "X-API-Key: ${API_KEY}" \
  "http://localhost:8000/v1/workspaces/${WORKSPACE_ID}/documents"

# Consulta RAG (scoped)
curl -X POST http://localhost:8000/v1/workspaces/${WORKSPACE_ID}/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{"query":"¿Que dice el documento?","top_k":3}'
```

### URLs de Acceso

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| API Readiness | http://localhost:8000/readyz |
| Métricas | http://localhost:8000/metrics |
| Worker Health | http://localhost:8001/healthz |
| MinIO (console) | http://localhost:9001 |

---

## Hardening Produccion (v4)

Para activar validaciones estrictas, definir `APP_ENV=production`.

Requisitos minimos:
- `JWT_SECRET` >= 32 chars y no default (fail-fast en prod).
- `JWT_COOKIE_SECURE=true` para cookies de auth.
- `METRICS_REQUIRE_AUTH=true` y `API_KEYS_CONFIG` o `RBAC_CONFIG` configurados (protege `/metrics`).
- CSP en prod sin `unsafe-inline` (ver `backend/app/security.py`).

Observabilidad:
- `/readyz` verifica dependencias core (DB).
- `/healthz?full=true` agrega chequeo de Google API si esta habilitado.
- `/metrics` exige API key con scope `metrics` o permiso `admin:metrics` cuando `METRICS_REQUIRE_AUTH=true`.

Seguridad frontend:
- La API key de servicio se guarda en `sessionStorage` (no persiste en `localStorage`).

---

## Scripts Útiles

| Script | Descripción |
|--------|-------------|
| `pnpm install` | Instalar dependencias del monorepo |
| `pnpm dev` | Levantar frontend + backend en modo desarrollo |
| `pnpm docker:up` | Iniciar PostgreSQL (db) + Backend (rag-api) |
| `pnpm docker:down` | Detener contenedores y eliminar volúmenes |
| `pnpm contracts:export` | Exportar OpenAPI desde FastAPI |
| `pnpm contracts:gen` | Generar cliente TypeScript con Orval |
| `pnpm test:backend:unit` | Tests unitarios backend (Docker) |
| `pnpm build` | Build de producción |
| `pnpm lint` | Lint del monorepo |
| `pnpm e2e` | Ejecutar Playwright (tests/e2e) |
| `pnpm e2e:ui` | Playwright UI |

### E2E (Playwright)

```bash
# Local (usa playwright.config.ts)
pnpm e2e

# Stack compose
E2E_USE_COMPOSE=1 TEST_API_KEY=<E2E_API_KEY> pnpm e2e
```

Ver `tests/e2e/README.md` para variables y detalles del stack.

### Backend (Python)

```bash
cd backend
pytest -m unit              # Tests unitarios (rápidos)
pytest -m integration       # Tests de integración (requiere DB)
pytest --cov=app            # Con cobertura
```

---

## Estructura del Repo

```
rag-corp/
├── backend/                 # FastAPI + lógica RAG
│   ├── app/
│   │   ├── domain/          # Entidades y Protocols
│   │   ├── application/     # Use cases
│   │   ├── infrastructure/  # Adapters (DB, APIs, chunking)
│   │   ├── main.py          # Entry point FastAPI
│   │   └── routes.py        # Controllers HTTP
│   └── tests/               # Unit + Integration tests
├── frontend/                # Next.js UI
│   ├── app/                 # App Router
│   └── __tests__/           # Tests frontend
├── shared/
│   └── contracts/           # OpenAPI + cliente TS generado
├── infra/
│   └── postgres/            # init.sql (schema + pgvector)
├── doc/                     # Documentación técnica
├── compose.yaml             # Docker Compose desarrollo
├── compose.prod.yaml        # Docker Compose producción
└── .env.example             # Template de variables
```

---

## Documentación

La documentación técnica vive en [`doc/`](doc/README.md):

| Documento | Descripción |
|-----------|-------------|
| [Arquitectura](doc/architecture/overview.md) | Capas, flujos, componentes |
| [API HTTP](doc/api/http-api.md) | Endpoints, auth, errores |
| [Schema DB](doc/data/postgres-schema.md) | PostgreSQL + pgvector |
| [Runbook Local](doc/runbook/local-dev.md) | Desarrollo y troubleshooting |
| [Tests](backend/tests/README.md) | Estructura y ejecución |

---

## Contribución y Calidad

### Tests

```bash
# Backend - unitarios (Docker, canónico)
pnpm test:backend:unit

# Backend - unitarios
cd backend && pytest -m unit -v

# Backend - con cobertura
pytest --cov=app --cov-report=html

# Frontend
cd frontend && pnpm test

# E2E (Playwright)
pnpm e2e
```

### Convenciones

- **Commits**: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`)
- **PRs**: Pequeños, una feature/fix por PR
- **Python**: PEP 8, type hints, docstrings CRC
- **TypeScript**: ESLint + Prettier

### Workflow

1. Fork y crear branch (`git checkout -b feat/mi-feature`)
2. Desarrollar con tests
3. Commit con mensaje descriptivo
4. Push y abrir PR
5. Actualizar docs si el cambio lo requiere

---

## Checklist v4 (100%)

- [x] Workspaces v4 + rutas nested para documentos y queries.
- [x] Scoping por workspace en repos y retrieval (SQL-level).
- [x] Legacy endpoints deprecated con `workspace_id` requerido.
- [x] Observabilidad: `/healthz`, `/readyz`, `/metrics` con auth en prod.
- [x] Hardening prod (APP_ENV, JWT_SECRET, JWT_COOKIE_SECURE, METRICS_REQUIRE_AUTH).
- [x] E2E v4: create -> upload -> READY -> chat scoped.
- [x] Docs actualizados (README + API + testing + e2e).

## Roadmap

### ✅ Implementado

- [x] Clean Architecture con capas bien definidas
- [x] API keys + scopes, RBAC por permisos
- [x] Rate limiting configurable
- [x] Metricas Prometheus y logging estructurado
- [x] Cache de embeddings (memory/Redis)
- [x] Chat streaming SSE con multi-turn (conversation_id)
- [x] UI de documentos (ingesta + CRUD)
- [x] CI con lint/test y E2E Playwright

### Post-v4 (ideas)

- [ ] Persistir conversaciones en Postgres (hoy in-memory)
- [ ] Admin UI avanzada (roles, claves, auditoria)
- [ ] Streaming observability (latency por token)

## Release Notes v4

- Workspaces v4 con rutas nested (`/v1/workspaces/{id}/*`) y ACL.
- Retrieval y documentos scopiados por workspace (sin cross-sources).
- Readiness `/readyz` y hardening prod para `/metrics`.
- E2E v4 con flujo create -> upload -> READY -> chat scoped.

---

## Licencia

Proprietary — personal/educational evaluation only. Commercial use and redistribution prohibited.

---

## Links

- 📖 [Documentación Completa](doc/README.md)
- 🐛 [Issues](https://github.com/SaintWyss/rag-corp/issues)
- 📊 [Swagger UI](http://localhost:8000/docs) (local)
