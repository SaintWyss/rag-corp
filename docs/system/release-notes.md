# Release Notes — RAG Corp

**Project:** RAG Corp  
**Last Updated:** 2026-01-24

---

## v6 (Current) — Workspace-First Architecture

**Release Date:** 2026-01-22  
**Status:** Production Ready

### Summary

v6 introduce **Workspaces** como unidad central de organización. Todas las operaciones de documentos y RAG ahora están scoped por `workspace_id`.

### New Features

- **Workspaces CRUD:** Crear, listar, editar, archivar workspaces
- **Visibilidad:** `PRIVATE`, `ORG_READ`, `SHARED` con ACL
- **Scoped Operations:** Todos los endpoints de documentos y RAG bajo `/v1/workspaces/{workspace_id}/...`
- **Publish/Share:** Publicar workspace a toda la org o compartir con usuarios específicos
- **Archive:** Soft-delete de workspaces (excluidos por defecto)
- **Worker HTTP Endpoints:** `/healthz`, `/readyz`, `/metrics` en puerto 8001
- **E2E Full Pipeline:** Tests que cubren el flujo completo con worker y storage

### Breaking Changes

| Area | v5 | v6 | Migration |
|------|----|----|-----------|
| Documents | `/v1/documents/*` | `/v1/workspaces/{ws_id}/documents/*` | Agregar `workspace_id` a todas las llamadas |
| Ask/Query | `/v1/ask`, `/v1/query` | `/v1/workspaces/{ws_id}/ask`, `/query` | Agregar `workspace_id` |
| Ingest | `/v1/ingest/*` | `/v1/workspaces/{ws_id}/ingest/*` | Agregar `workspace_id` |

**Legacy endpoints:** Siguen funcionando pero requieren `?workspace_id=...` y están marcados como **DEPRECATED**.

### Database Migrations

| Migration | Description |
|-----------|-------------|
| `007_add_workspaces_and_acl.py` | Crea tablas `workspaces`, `workspace_acl` |
| `008_docs_workspace_id.py` | Agrega `workspace_id` a documents, crea workspace Legacy para backfill |

### Known Issues

- E2E tests de CSP header pendientes
- Runbook de rollback incompleto

---

## v5 — Async Upload Pipeline

**Release Date:** 2026-01-10

### Summary

Introduce procesamiento asíncrono de documentos con RQ Worker.

### Features

- **Async Upload:** Upload retorna 202, worker procesa en background
- **Document States:** PENDING → PROCESSING → READY/FAILED
- **S3/MinIO Storage:** Binarios almacenados externamente
- **Redis Queue:** Jobs de procesamiento via RQ

### Breaking Changes

- Upload ya no es síncrono (polling/websocket para estado)

---

## v4 — RBAC and Audit

**Release Date:** 2026-01-05

### Summary

Agrega RBAC para API keys y auditoría de eventos.

### Features

- **API Keys + RBAC:** Control granular de permisos
- **Audit Events:** Registro de acciones críticas
- **Admin Endpoints:** Gestión de usuarios

---

## v3 — Dual Auth

**Release Date:** 2025-12-20

### Features

- **JWT Auth:** Para UI (cookies httpOnly)
- **API Key Auth:** Para integraciones
- **User Roles:** admin/employee

---

## v2 — Clean Architecture

**Release Date:** 2025-12-10

### Summary

Refactor a Clean Architecture (Domain/Application/Infrastructure).

### Features

- Separación de capas
- Ports/Adapters pattern
- DI container

---

## v1 — MVP

**Release Date:** 2025-12-01

### Features

- Ingesta básica de documentos
- Búsqueda vectorial con pgvector
- LLM con Google Gemini
- UI básica Next.js

---

## Upgrade Guide

### v5 → v6

1. **Migraciones:**
   ```bash
   pnpm db:migrate
   ```
   Esto crea workspace "Legacy" y backfillea documents existentes.

2. **Actualizar llamadas API:**
   - Reemplazar `/v1/documents` → `/v1/workspaces/{ws_id}/documents`
   - Crear workspaces para organizar documentos

3. **Actualizar frontend:**
   - Agregar selector de workspace
   - Actualizar rutas a nested paths

### Rollback v6 → v5

```bash
cd apps/backend
alembic downgrade 006
```

⚠️ **Warning:** Esto elimina datos de workspaces y ACL.

---

## Deprecations

| Deprecated | Replacement | Removal Target |
|------------|-------------|----------------|
| `/v1/documents` | `/v1/workspaces/{ws_id}/documents` | v8 |
| `/v1/ask` | `/v1/workspaces/{ws_id}/ask` | v8 |
| `/v1/query` | `/v1/workspaces/{ws_id}/query` | v8 |
| `/v1/ingest/*` | `/v1/workspaces/{ws_id}/ingest/*` | v8 |
