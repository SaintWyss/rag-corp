# ADR-005: Unicidad de Workspace por owner_user_id + name

## Estado

**Aceptado** (2026-01-15) — Vigente

## Contexto

- La entidad Workspace indica que `name` puede ser unico por owner o global (decision pendiente). (Fuente **Especificación Base**: `docs/project/informe_de_sistemas_rag_corp.md`)
- La especificacion **Especificación Base** fija ownership por usuario (cada \"Seccion\" UI tiene `owner_user_id`). (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)
- El caso de uso de creacion contempla 409 por duplicado si se elige unicidad por owner. (Fuente **Especificación Base**: `docs/project/informe_de_sistemas_rag_corp.md`)

## Decision

- La unicidad de Workspace sera por `(owner_user_id, name)`. (Fuente **Especificación Base**: `docs/project/informe_de_sistemas_rag_corp.md`)
- Se permite repetir `name` entre owners distintos; si el mismo owner repite, responde 409. (Fuente **Especificación Base**: `docs/project/informe_de_sistemas_rag_corp.md`)

## Alternativas consideradas

1. Unicidad global del `name` (descartado; la especificacion **Especificación Base** explicita que puede ser por owner o global y se opta por owner). (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)

## Consecuencias

- La UI debe manejar error 409 por duplicados en creacion. (Fuente **Especificación Base**: `docs/project/informe_de_sistemas_rag_corp.md`)
- El backend y la DB deben aplicar el constraint compuesto `(owner_user_id, name)` alineado al modelo. (Fuente **Especificación Base**: `docs/project/informe_de_sistemas_rag_corp.md`)

## Impacto FE/BE/DB

- FE: validar y mostrar conflicto 409 en creacion de workspace (\"Seccion\" solo UI). (Fuente **Especificación Base**: `docs/project/informe_de_sistemas_rag_corp.md`)
- BE/API: aplicar unicidad por owner en el caso de uso de creacion. (Fuente **Especificación Base**: `docs/project/informe_de_sistemas_rag_corp.md`)
- DB: constraint unico en `(owner_user_id, name)` sobre `workspaces`. (Fuente **Especificación Base**: `docs/project/informe_de_sistemas_rag_corp.md`)

## Validacion

- `pnpm test:backend:unit` (Fuente: `docs/quality/testing.md`, "Unit tests (Docker, recomendado)")
- `pnpm -C apps/frontend test` (Fuente: `docs/quality/testing.md`, "Frontend (Jest)")
- `pnpm e2e` (ver `docs/quality/testing.md` y `tests/e2e/README.md`)
