# ADR-005: Unicidad de Workspace por owner_user_id + name

## Estado

**Aceptado** (2026-01-15) — Vigente en v6

## Contexto

- La entidad Workspace indica que `name` puede ser unico por owner o global (decision pendiente). (Fuente **Especificación Base**: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 7.2 Entidad Workspace")
- La especificacion **Especificación Base** fija ownership por usuario (cada \"Seccion\" UI tiene `owner_user_id`). (Fuente: `.github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md`, "RB-01 Ownership")
- El caso de uso de creacion contempla 409 por duplicado si se elige unicidad por owner. (Fuente **Especificación Base**: `.github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md`, "UC-10 — Crear seccion", "Duplicado (si se decide unique por owner) -> 409")

## Decision

- La unicidad de Workspace sera por `(owner_user_id, name)`. (Fuente **Especificación Base**: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 7.2 Entidad Workspace")
- Se permite repetir `name` entre owners distintos; si el mismo owner repite, responde 409. (Fuente **Especificación Base**: `.github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md`, "Duplicado (si se decide unique por owner) -> 409")

## Alternativas consideradas

1. Unicidad global del `name` (descartado; la especificacion **Especificación Base** explicita que puede ser por owner o global y se opta por owner). (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 7.2 Entidad Workspace")

## Consecuencias

- La UI debe manejar error 409 por duplicados en creacion. (Fuente **Especificación Base**: `.github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md`, "Duplicado (si se decide unique por owner) -> 409")
- El backend y la DB deben aplicar el constraint compuesto `(owner_user_id, name)` alineado al modelo. (Fuente **Especificación Base**: `.github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md`, "RB-01 Ownership"; `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 7.2 Entidad Workspace")

## Impacto FE/BE/DB

- FE: validar y mostrar conflicto 409 en creacion de workspace (\"Seccion\" solo UI). (Fuente **Especificación Base**: `.github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md`, "UC-10 — Crear seccion", "Duplicado -> 409")
- BE/API: aplicar unicidad por owner en el caso de uso de creacion. (Fuente **Especificación Base**: `.github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md`, "RB-01 Ownership"; `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "`owner_user_id`", "`name`")
- DB: constraint unico en `(owner_user_id, name)` sobre `workspaces`. (Fuente **Especificación Base**: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 7.2 Entidad Workspace", "### 12.2 Tablas nuevas")

## Validacion

- `pnpm test:backend:unit` (Fuente: `docs/quality/testing.md`, "Unit tests (Docker, recomendado)")
- `pnpm -C apps/frontend test` (Fuente: `docs/quality/testing.md`, "Frontend (Jest)")
- `pnpm e2e` (Fuente: `docs/quality/testing.md`, "Ejecutar E2E con apps/backend/frontend locales")
