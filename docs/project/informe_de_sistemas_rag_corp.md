# Informe de Sistemas — RAG Corp

**Autor:** Santiago Scacciaferro  
**Fecha:** 2026-02-04 (America/Argentina/Cordoba)  
**Repo:** `rag-corp`

---

## Fuente de verdad (anti-drift)

Regla: si un documento contradice a otro, manda el de **mayor prioridad**.

1. **Sistema (este documento)**: `docs/project/informe_de_sistemas_rag_corp.md`
2. **Contrato API**: `shared/contracts/openapi.json` (+ `shared/contracts/src/generated.ts`)
3. **Datos**: `apps/backend/alembic/versions/*` + `docs/reference/data/postgres-schema.md`
4. **Runtime real**: `compose.yaml`, `.github/workflows/*`, `apps/frontend/next.config.mjs`, `apps/backend/app/main.py`, `apps/backend/app/api/main.py`
5. **Decisiones**: `docs/architecture/overview.md` + `docs/architecture/adr/*.md`

---

## 1. Introducción y Alcance

### 1.1 Problema (AS-IS)

RAG Corp ya resuelve la parte “técnica pesada” de un sistema RAG:

- UI Next.js tipo “Sources” para documentos y Q&A.
- Backend FastAPI con Clean Architecture (Domain / Application / Infrastructure / Interfaces).
- PostgreSQL + pgvector para chunks y embeddings.
- Ingesta y upload con pipeline asíncrono (Redis/RQ/worker).
- Dual auth: JWT para usuarios + API keys con RBAC.
- Observabilidad y CI con suites unit/integration/e2e.

Pain points (negocio/seguridad):

- Falta gobernanza clara por contexto de conocimiento.
- Mezcla de fuentes eleva riesgo de fuga de información.
- Necesidad de hardening explícito en producción (fail-fast, CSP, métricas protegidas).

### 1.2 Objetivos

- Gestionar conocimiento por **Workspaces** ("Sección" solo UI) con permisos claros.
- Consultas siempre acotadas a un workspace (scoping total).
- Auditoría operable y observabilidad completa.
- Contratos OpenAPI como anti-drift FE/BE.

### 1.3 Alcance

**In-Scope**
- CRUD de workspaces con visibilidad `PRIVATE | ORG_READ | SHARED` (+ `workspace_acl`).
- Documentos dentro de workspace: upload/list/get/delete/reprocess con estados `PENDING | PROCESSING | READY | FAILED`.
- RAG scoped: ask/query/stream siempre con `workspace_id`.
- Auditoría de eventos críticos (auth/workspace/document).
- Observabilidad: `/healthz`, `/readyz`, `/metrics` para API y worker.

**Out-of-Scope (por ahora)**
- Multi-tenant por empresa.
- SSO/LDAP.
- OCR avanzado obligatorio para PDFs escaneados.
- Workflows complejos de aprobación/firma.

### 1.4 Supuestos y restricciones

**Supuestos**
- Organización única con usuarios `admin/employee`.
- Embeddings/LLM provistos por Google GenAI (fakes habilitables para dev/tests).
- Binarios en S3-compatible (MinIO on-prem o S3 cloud).

**Restricciones**
- Compatible con operación local vía Docker Compose.
- Respetar Clean Architecture (Domain no depende de frameworks/infra).
- Errores HTTP en RFC7807 (`application/problem+json`).

### 1.5 Glosario mínimo

- **Workspace:** contenedor lógico de documentos y chat; unidad de permisos.
- **Owner:** usuario asignado al workspace; controla escritura/borrado/reprocess (junto a admin).
- **Visibility:** `PRIVATE | ORG_READ | SHARED`.
- **ACL:** lista explícita `workspace_acl` para visibilidad `SHARED`.
- **Chunk:** fragmento de documento con embedding.

---

## 2. Arquitectura y Stack

### 2.1 Arquitectura

**Patrón:** Clean Architecture.  
**Justificación:** aislar reglas de negocio, permitir reemplazo de proveedores y asegurar testabilidad.

**Reglas de dependencia**
- Domain no depende de Application/Infrastructure/Interfaces.
- Application depende de Domain y puertos.
- Infrastructure implementa puertos (DB, storage, queue, LLM).
- Interfaces adaptan HTTP y traducen errores → RFC7807.

### 2.2 Componentes

- **Frontend (Next.js)**: navegación, selector de workspace, UI Sources/Chat, panel admin.
- **Backend API (FastAPI)**: auth, workspaces, documents, query/ask/stream, métricas.
- **Worker (RQ)**: procesamiento asíncrono de documentos.
- **PostgreSQL + pgvector**: relacional + vector store.
- **Redis**: cola RQ (y cache opcional).
- **S3/MinIO**: almacenamiento de binarios.

### 2.3 Stack (versiones)

- Frontend: Next.js 16.1.1, React 19.2.3, TypeScript ^5, Tailwind ^4.
- Backend: Python 3.11, FastAPI 0.128.0, SQLAlchemy >=2.0, Alembic >=1.13, psycopg 3.3.2.
- Datos: PostgreSQL 16, pgvector 0.8.1.
- IA: google-genai 1.57.0 (embeddings `text-embedding-004`, 768D).
- Queue/Cache: Redis 7-alpine, RQ >=1.16.0.

---

## 3. Modelo de Datos (resumen)

Tablas núcleo:

- `users`
- `workspaces` (incluye `owner_user_id`, `visibility`, `archived_at`)
- `workspace_acl`
- `documents` (incluye `workspace_id`, `status`, `storage_key`, `deleted_at`)
- `chunks` (incluye `embedding vector(768)`, `document_id`)
- `audit_events`

Reglas clave:

- `documents.workspace_id` es obligatorio desde el inicio (sin backfill).
- Unicidad: `unique(owner_user_id, name)` en `workspaces`.
- Archiving: `workspaces.archived_at` y soft-delete en documentos.

---

## 4. API (superficie canónica)

- `/auth/*` para login/logout/me.
- `/v1/workspaces/*` para CRUD y visibilidad.
- `/v1/workspaces/{workspace_id}/documents/*` para documentos.
- `/v1/workspaces/{workspace_id}/ask` y `/v1/workspaces/{workspace_id}/ask/stream` para RAG.
- `/v1/workspaces/{workspace_id}/query` para retrieval.
- `/v1/workspaces/{workspace_id}/ingest/text` y `/v1/workspaces/{workspace_id}/ingest/batch` para ingestión directa.

Contrato canónico: `shared/contracts/openapi.json`.

---

## 5. UI (mapa de navegación)

- `/login`
- `/workspaces`
- `/workspaces/{id}` (Sources)
- `/workspaces/{id}/chat`
- `/admin/users`

---

## 6. Observabilidad y Operación

- API: `/healthz`, `/readyz`, `/metrics`.
- Worker: `/readyz` y métricas (si habilitado).
- Runbooks: `docs/runbook/*`.

---

## 7. Definition of Done (global)

1. Workspaces completos (CRUD + visibilidad + share).
2. Documentos y consultas 100% scoped por workspace.
3. Permisos: owner/admin write; viewers read+chat.
4. UI: Workspaces + Sources/Chat por workspace.
5. Auditoría por workspace.
6. Hardening prod: secrets/config + métricas protegidas.
7. CI `e2e-full` (admin): login → crear workspace → upload → READY → chat.
