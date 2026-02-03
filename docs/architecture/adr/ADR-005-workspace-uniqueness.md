# ADR-005: Unicidad de Workspace por owner_user_id + name

## Estado

**Aceptado** (2026-01-15) — Vigente en v6

## Contexto

- La entidad Workspace indica que `name` puede ser unico por owner o global (decision pendiente). (Fuente **Especificación Base**: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)
- La especificacion **Especificación Base** fija ownership por usuario (cada \"Seccion\" UI tiene `owner_user_id`). (Fuente: `TODO(verify: missing .github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md)`)
- El caso de uso de creacion contempla 409 por duplicado si se elige unicidad por owner. (Fuente **Especificación Base**: `TODO(verify: missing .github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md)`)

## Decision

- La unicidad de Workspace sera por `(owner_user_id, name)`. (Fuente **Especificación Base**: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)
- Se permite repetir `name` entre owners distintos; si el mismo owner repite, responde 409. (Fuente **Especificación Base**: `TODO(verify: missing .github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md)`)

## Alternativas consideradas

1. Unicidad global del `name` (descartado; la especificacion **Especificación Base** explicita que puede ser por owner o global y se opta por owner). (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)

## Consecuencias

- La UI debe manejar error 409 por duplicados en creacion. (Fuente **Especificación Base**: `TODO(verify: missing .github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md)`)
- El backend y la DB deben aplicar el constraint compuesto `(owner_user_id, name)` alineado al modelo. (Fuente **Especificación Base**: `TODO(verify: missing .github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md)`; `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)

## Impacto FE/BE/DB

- FE: validar y mostrar conflicto 409 en creacion de workspace (\"Seccion\" solo UI). (Fuente **Especificación Base**: `TODO(verify: missing .github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md)`)
- BE/API: aplicar unicidad por owner en el caso de uso de creacion. (Fuente **Especificación Base**: `TODO(verify: missing .github/rag_corp_informe_de_analisis_y_especificacion_v_4_→_secciones.md)`; `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)
- DB: constraint unico en `(owner_user_id, name)` sobre `workspaces`. (Fuente **Especificación Base**: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)

## Validacion

- `pnpm test:backend:unit` (Fuente: `docs/quality/testing.md`, "Unit tests (Docker, recomendado)")
- `pnpm -C apps/frontend test` (Fuente: `docs/quality/testing.md`, "Frontend (Jest)")
- `pnpm e2e` (Fuente: `docs/quality/testing.md`, "Ejecutar E2E con apps/backend/frontend locales")
