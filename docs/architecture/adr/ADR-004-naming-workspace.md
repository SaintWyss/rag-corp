# ADR-004: Naming de Workspace (API/codigo) y Seccion (UI)

## Estado

**Aceptado** (2026-01-15) — Vigente

## Contexto

- La especificacion **Especificación Base** define el naming tecnico: en codigo se usa Workspace, en UI se muestra Seccion, y la fuente de verdad tecnica es Workspace. (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)
- La API propuesta expone rutas bajo `/v1/workspaces`. (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)
- La UI propuesta usa el label "Workspaces/Secciones" y un selector de workspace. (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)

## Decision

- Usar **workspace** como termino tecnico en API/contratos/BE/DB; **seccion** queda solo como copy/label en UI. (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)
- Documentar el mapping UI -> workspace como convencion de producto para evitar drift entre capas. (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)

## Alternativas consideradas

1. "Seccion" en API/DB/codigo (descartado porque la decision **Especificación Base** fija Workspace como termino tecnico). (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)
2. "Workspace" tambien en UI (descartado porque la **Especificación Base** permite Seccion en UI para ser natural en espanol). (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)

## Consecuencias

- Las rutas y contratos tecnicos se alinean a `/v1/workspaces` y a la entidad Workspace. (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)
- La UI mantiene el termino "Seccion" sin cambiar el contrato tecnico. (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)

## Impacto FE/BE/DB

- FE: navegacion y copy con "Workspaces/Secciones" y selector de workspace. (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)
- BE/API: endpoints `/v1/workspaces/...`. (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)
- DB: entidad `workspaces` y atributos definidos para Workspace. (Fuente: `docs/project/informe_de_sistemas_rag_corp.md`)

## Validacion

- `pnpm test:backend:unit` (Fuente: `docs/quality/testing.md`, "Unit tests (Docker, recomendado)")
- `pnpm -C apps/frontend test` (Fuente: `docs/quality/testing.md`, "Frontend (Jest)")
- `pnpm e2e` (ver `docs/quality/testing.md` y `tests/e2e/README.md`)
