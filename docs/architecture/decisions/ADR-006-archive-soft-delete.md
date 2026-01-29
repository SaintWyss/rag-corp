# ADR-006: Archive/soft-delete de Workspaces y Documentos

## Estado

**Aceptado** (2026-01-15) — Vigente en v6

## Contexto

- El modelo de Workspace incluye `archived_at` como soft archive. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)
- La API propuesta incorpora `POST /v1/workspaces/{id}/archive` y la UI permite archivar. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)
- La politica de borrado propone la opcion B (soft delete de seccion y documentos asociados). (Fuente: `TODO(verify: missing .github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md)`)
- El modelo conceptual incluye `deleted_at` para Section/Document. (Fuente: `TODO(verify: missing .github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md)`)
- La auditoria debe registrar eventos criticos y guardar `workspace_id` cuando aplique. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)

## Decision

- Archive es soft-delete: se marca `archived_at` en Workspace y se marca `deleted_at` en documentos asociados, preservando historico. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`; `TODO(verify: missing .github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md)`)
- Workspaces archivados quedan fuera de listados por defecto y no aceptan upload/ask; los documentos archivados no participan en retrieval. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)
- Se registra evento de auditoria para archive/unarchive con `workspace_id` como parte de la trazabilidad. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)

## Alternativas consideradas

1. Opcion A: impedir borrado de seccion con documentos (descartado en favor de soft delete). (Fuente: `TODO(verify: missing .github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md)`)

## Consecuencias

- Se preserva auditabilidad y posibilidad de restore al mantener `archived_at`/`deleted_at`. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`; `TODO(verify: missing .github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md)`)
- La UI debe mostrar acciones de archivar y evitar operaciones sobre workspaces archivados. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)

## Impacto FE/BE/DB

- FE: controles de "archivar" y estados en listados de workspaces. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)
- BE/API: endpoint `POST /v1/workspaces/{id}/archive` y reglas de acceso owner/admin. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)
- DB: `workspaces.archived_at` y `documents.deleted_at` como marcas de soft-delete. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`; `TODO(verify: missing .github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md)`)

## Validacion

- `pnpm test:backend:unit` (Fuente: `docs/quality/testing.md`, "Unit tests (Docker, recomendado)")
- `pnpm --filter web test` (Fuente: `docs/quality/testing.md`, "Todos los tests")
- `pnpm e2e` (Fuente: `docs/quality/testing.md`, "Ejecutar E2E con apps/backend/frontend locales")
