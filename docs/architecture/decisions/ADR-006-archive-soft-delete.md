# ADR-006: Archive/soft-delete de Workspaces y Documentos

## Estado

**Aceptado** (2026-01-15) — Vigente en v6

## Contexto

- El modelo de Workspace incluye `archived_at` como soft archive. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 7.2 Entidad Workspace")
- La API propuesta incorpora `POST /v1/workspaces/{id}/archive` y la UI permite archivar. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 13.2 Endpoints propuestos", "### 14.2 Pantalla Workspaces")
- La politica de borrado propone la opcion B (soft delete de seccion y documentos asociados). (Fuente: `.github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md`, "RB-06 Borrado de seccion")
- El modelo conceptual incluye `deleted_at` para Section/Document. (Fuente: `.github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md`, "### 11.1 Entidades")
- La auditoria debe registrar eventos criticos y guardar `workspace_id` cuando aplique. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "RF-E1: registrar eventos criticos", "### 12.4 Auditoria por workspace")

## Decision

- Archive es soft-delete: se marca `archived_at` en Workspace y se marca `deleted_at` en documentos asociados, preservando historico. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 7.2 Entidad Workspace"; `.github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md`, "RB-06 Borrado de seccion", "### 11.1 Entidades")
- Workspaces archivados quedan fuera de listados por defecto y no aceptan upload/ask; los documentos archivados no participan en retrieval. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "POST /v1/workspaces/{id}/archive", "RF-D2: retrieval solo de documentos del workspace")
- Se registra evento de auditoria para archive/unarchive con `workspace_id` como parte de la trazabilidad. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "RF-E1: registrar eventos criticos", "### 12.4 Auditoria por workspace")

## Alternativas consideradas

1. Opcion A: impedir borrado de seccion con documentos (descartado en favor de soft delete). (Fuente: `.github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md`, "RB-06 Borrado de seccion")

## Consecuencias

- Se preserva auditabilidad y posibilidad de restore al mantener `archived_at`/`deleted_at`. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 7.2 Entidad Workspace"; `.github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md`, "### 11.1 Entidades")
- La UI debe mostrar acciones de archivar y evitar operaciones sobre workspaces archivados. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 14.2 Pantalla Workspaces")

## Impacto FE/BE/DB

- FE: controles de "archivar" y estados en listados de workspaces. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 14.2 Pantalla Workspaces")
- BE/API: endpoint `POST /v1/workspaces/{id}/archive` y reglas de acceso owner/admin. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "POST /v1/workspaces/{id}/archive — archivar (owner/admin)")
- DB: `workspaces.archived_at` y `documents.deleted_at` como marcas de soft-delete. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "`archived_at` (soft archive)"; `.github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md`, "Section(... deleted_at?)", "Document(... deleted_at)")

## Validacion

- `pnpm test:backend:unit` (Fuente: `docs/quality/testing.md`, "Unit tests (Docker, recomendado)")
- `pnpm --filter web test` (Fuente: `docs/quality/testing.md`, "Todos los tests")
- `pnpm e2e` (Fuente: `docs/quality/testing.md`, "Ejecutar E2E con apps/backend/frontend locales")
