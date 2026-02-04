# ADR-006: Archive/soft-delete de Workspaces y Documentos

## Estado

**Aceptado** (2026-01-15) — Vigente

## Contexto

- El modelo de Workspace incluye `archived_at` como soft archive. (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)
- La API propuesta incorpora `POST /v1/workspaces/{id}/archive` y la UI permite archivar. (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)
- La politica de borrado propone la opcion B (soft delete de seccion y documentos asociados). (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)
- El modelo conceptual incluye `deleted_at` para Section/Document. (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)
- La auditoria debe registrar eventos criticos y guardar `workspace_id` cuando aplique. (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)

## Decision

- Archive es soft-delete: se marca `archived_at` en Workspace y se marca `deleted_at` en documentos asociados, preservando historico. (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)
- Workspaces archivados quedan fuera de listados por defecto y no aceptan upload/ask; los documentos archivados no participan en retrieval. (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)
- Se registra evento de auditoria para archive/unarchive con `workspace_id` como parte de la trazabilidad. (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)

## Alternativas consideradas

1. Opcion A: impedir borrado de seccion con documentos (descartado en favor de soft delete). (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)

## Consecuencias

- Se preserva auditabilidad y posibilidad de restore al mantener `archived_at`/`deleted_at`. (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)
- La UI debe mostrar acciones de archivar y evitar operaciones sobre workspaces archivados. (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)

## Impacto FE/BE/DB

- FE: controles de "archivar" y estados en listados de workspaces. (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)
- BE/API: endpoint `POST /v1/workspaces/{id}/archive` y reglas de acceso owner/admin. (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)
- DB: `workspaces.archived_at` y `documents.deleted_at` como marcas de soft-delete. (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)

## Validacion

- `pnpm test:backend:unit` (Fuente: `docs/quality/testing.md`, "Unit tests (Docker, recomendado)")
- `pnpm --filter web test` (Fuente: `docs/quality/testing.md`, "Todos los tests")
- `pnpm e2e` (ver `docs/quality/testing.md` y `tests/e2e/README.md`)
