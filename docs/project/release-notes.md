# Release Notes — RAG Corp

**Project:** RAG Corp  
**Last Updated:** 2026-02-04

---

## Baseline — Workspace-First Architecture

**Release Date:** 2026-01-22  
**Status:** Production Ready

### Summary

Esta entrega define el baseline actual con **Workspaces** como unidad central de organizacion. Todas las operaciones de documentos y RAG estan scoped por `workspace_id`.

### Highlights

- **Workspaces CRUD:** crear, listar, editar, archivar workspaces.
- **Visibilidad:** `PRIVATE`, `ORG_READ`, `SHARED` con ACL.
- **Operaciones scoped:** endpoints de documentos y RAG bajo `/v1/workspaces/{workspace_id}/...`.
- **Publish/Share:** publicar a la org o compartir con usuarios.
- **Archive:** soft-delete de workspaces (excluidos por defecto).
- **Worker HTTP Endpoints:** `/healthz`, `/readyz`, `/metrics` en puerto 8001.
- **E2E Full Pipeline:** tests que cubren el flujo completo con worker y storage.

### API Surface (canonical)

- `/v1/workspaces/{workspace_id}/documents/*`
- `/v1/workspaces/{workspace_id}/ask`
- `/v1/workspaces/{workspace_id}/ask/stream`
- `/v1/workspaces/{workspace_id}/query`
- `/v1/workspaces/{workspace_id}/ingest/text`
- `/v1/workspaces/{workspace_id}/ingest/batch`

### Database Migrations

- `001_foundation.py`: baseline completo del schema (incluye workspaces y ACL).
- Ver politica de migraciones en `docs/reference/data/migrations-policy.md`.

### Known Issues

- E2E tests de CSP header pendientes.
- Runbook de rollback incompleto.
