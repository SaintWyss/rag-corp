# Documentacion RAG Corp

**Last Updated:** 2026-01-15

Esta carpeta contiene la documentacion viva del proyecto. El quickstart esta en `../README.md`.
Este README concentra solo informacion vigente y enlaces; los reportes historicos se resumen al final.

## Indice

- `../README.md` - Quickstart y overview
- `architecture/overview.md` - Arquitectura, capas y flujo RAG
- `architecture/decisions/ADR-001-clean-architecture.md` - ADR Clean Architecture
- `architecture/decisions/ADR-002-pgvector.md` - ADR pgvector
- `architecture/decisions/ADR-003-google-gemini.md` - ADR Google Gemini
- `architecture/decisions/ADR-004-naming-workspace.md` - ADR naming v4: workspace (API/codigo) vs seccion (UI)
- `architecture/decisions/ADR-005-workspace-uniqueness.md` - ADR unicidad v4 de workspace por owner_user_id + name
- `architecture/decisions/ADR-006-archive-soft-delete.md` - ADR archive/soft-delete v4 para workspaces y documentos
- `architecture/decisions/ADR-007-legacy-endpoints.md` - ADR compatibilidad v4 de endpoints legacy vs nested
- `api/http-api.md` - Endpoints, contratos y ejemplos
- `api/rbac.md` - Role-Based Access Control (RBAC)
- `data/postgres-schema.md` - Schema e indices pgvector
- `runbook/local-dev.md` - Desarrollo local y comandos utiles
- `runbook/migrations.md` - Migraciones con Alembic
- `runbook/troubleshooting.md` - Troubleshooting operativo
- `runbook/kubernetes.md` - Deployment en Kubernetes
- `quality/testing.md` - Estrategia de testing
- `../tests/e2e/README.md` - Playwright E2E (local + CI)
- `../backend/tests/README.md` - Tests (unit + integration)
- `../shared/contracts/openapi.json` - OpenAPI (fuente de verdad)
- `../shared/contracts/src/generated.ts` - Cliente TypeScript generado
- [Resumen del sistema](#resumen-del-sistema)
- [Flujos principales](#flujos-principales)
- [Arquitectura (resumen)](#arquitectura-resumen)
- [Operacion y calidad](#operacion-y-calidad)
- [Release notes v4](#release-notes-v4)
- [Reportes historicos (resumen)](#reportes-historicos-resumen)

## Estructura minima

```
doc/
├── README.md
├── architecture/
│   ├── overview.md
│   └── decisions/        # ADRs
├── api/
│   ├── http-api.md
│   └── rbac.md           # RBAC documentation
├── data/
│   └── postgres-schema.md
├── design/
│   └── patterns.md
├── quality/
│   └── testing.md
└── runbook/
    ├── local-dev.md
    ├── migrations.md
    └── kubernetes.md     # K8s deployment guide
```

## Mantenimiento

- Actualiza `Last Updated` cuando cambien rutas, schema o runbook.
- Contratos: seguir el flujo `pnpm contracts:export` + `pnpm contracts:gen` (ver `api/http-api.md`).

### ⚠️ Regla de Oro: Docs + Codigo en el mismo PR

Para evitar que la documentacion se desincronice del codigo:

1. **Si cambias un endpoint** → actualiza `api/http-api.md`
2. **Si cambias el schema de DB** → actualiza `data/postgres-schema.md`
3. **Si agregas una variable de entorno** → actualiza `.env.example` y `runbook/local-dev.md`
4. **Si cambias la estructura de carpetas** → actualiza `architecture/overview.md`

> 💡 **Tip:** Antes de abrir un PR, preguntate: "¿Que documentacion afecta este cambio?"

## Resumen del sistema

RAG Corp es un sistema de Retrieval-Augmented Generation que permite ingestar documentos, buscarlos
semanticamente y responder preguntas con un LLM usando contexto recuperado para reducir alucinaciones.

Arquitectura de alto nivel:

```
UI (Next.js) -> API (FastAPI) -> PostgreSQL + pgvector
                     |                |
                     |                v
                     |           S3/MinIO
                     v
                Redis Queue -> Worker -> Gemini (embeddings + LLM)
```

## Flujos principales

- **Auth JWT** (`POST /auth/login`, `GET /auth/me`, `POST /auth/logout`): login UI con JWT + cookie.
- **Ingest** (`POST /v1/ingest/text`): valida, chunking, genera embeddings y guarda documento + chunks.
- **Upload async** (`POST /v1/documents/upload`): guarda archivo en S3/MinIO y deja `status=PENDING`.
- **Worker** (`python -m app.worker`): procesa documentos PENDING → READY/FAILED.
- **Documentos** (`GET /v1/documents`, `GET/DELETE /v1/documents/{id}`): lista, detalle y borrado.
- **Reprocess** (`POST /v1/documents/{id}/reprocess`): reintenta pipeline async.
- **Query** (`POST /v1/query`): embebe la consulta y recupera los top-k chunks mas similares.
- **Ask** (`POST /v1/ask`): recupera chunks, arma contexto y el LLM genera la respuesta con fuentes.
- **Ask Stream** (`POST /v1/ask/stream`): igual que Ask pero con streaming SSE token-by-token y conversation_id.

## Arquitectura (resumen)

- **Clean Architecture**: domain -> application -> infrastructure -> API.
- **Backend**: use cases en `backend/app/application`, adapters en `backend/app/infrastructure`.
- **Frontend**: Next.js App Router con vistas Ask, Documents y Chat streaming.
- **Contratos**: OpenAPI es la fuente de verdad y se genera cliente TypeScript con Orval.

## Operacion y calidad

- **Observabilidad**: logs estructurados, metricas Prometheus y health check en `/healthz`.
- **Seguridad**: dual-auth (JWT usuarios + X-API-Key), RBAC por permisos y rate limiting.
- **Testing**: unit + integration en backend, tests de UI en frontend, E2E con Playwright; ver `../tests/e2e/README.md`.
- **Infra local**: `compose.yaml` y pasos en `runbook/local-dev.md`.
- **Infra K8s**: manifests production-ready en `../infra/k8s/`; ver `runbook/kubernetes.md`.
- **Migraciones**: Alembic para schema evolution; ver `runbook/migrations.md`.
- **Storage**: S3/MinIO para archivos; metadata en Postgres.
- **Worker**: health/metrics propio en `:8001` (ver `runbook/troubleshooting.md`).
- **Cache**: In-memory por defecto, Redis en produccion (auto-detectado via `REDIS_URL`).

## Release Notes v4

- Auth JWT (admin/employee) + dual-auth con X-API-Key.
- Upload async a S3/MinIO con pipeline worker (PENDING/PROCESSING/READY/FAILED).
- ACL basico por documento (`allowed_roles`, owner).
- Audit log de eventos clave.
- UI Sources con upload, estados y reproceso.

## Reportes historicos (resumen)

### Migración Estructural - Option A (2026-01-02)

- Aplanado del monorepo a `frontend/`, `backend/` y `shared/`.
- Actualizacion de scripts, compose y docs para los nuevos paths.

### Auditoría de Implementación - HITOs H9-H25 (2025-01-02)

- Hitos de infraestructura y calidad (CI/CD, error catalog, deploy, cache, SSE, observabilidad, seguridad, accesibilidad).
- Detalle historico removido de este README; consultar el historial si es necesario.

### Auditoría Completa - RAG Corp (2026-01-03)

- Arquitectura y practicas bien establecidas.
- Deuda tecnica priorizada: resiliencia en APIs externas; streaming, cache y CI/CD quedaron implementados en v3.

### Readiness Review — 2026-01-02

- Status READY con limitaciones por falta de Docker en el entorno de verificacion.

### Readiness Review - 2026-01-03

- Status READY; ajustes para ejecutar unit tests offline sin variables de entorno.
