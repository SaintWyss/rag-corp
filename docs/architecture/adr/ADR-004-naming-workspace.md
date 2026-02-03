# ADR-004: Naming de Workspace (API/codigo) y Seccion (UI)

## Estado

**Aceptado** (2026-01-15) — Vigente en v6

## Contexto

- La especificacion **Especificación Base** define el naming tecnico: en codigo se usa Workspace, en UI se muestra Seccion, y la fuente de verdad tecnica es Workspace. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)
- La API propuesta expone rutas bajo `/v1/workspaces`. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)
- La UI propuesta usa el label "Workspaces/Secciones" y un selector de workspace. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)

## Decision

- Usar **workspace** como termino tecnico en API/contratos/BE/DB; **seccion** queda solo como copy/label en UI. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)
- Documentar el mapping UI -> workspace como convencion de producto para evitar drift entre capas. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)

## Alternativas consideradas

1. "Seccion" en API/DB/codigo (descartado porque la decision **Especificación Base** fija Workspace como termino tecnico). (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)
2. "Workspace" tambien en UI (descartado porque la **Especificación Base** permite Seccion en UI para ser natural en espanol). (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)

## Consecuencias

- Las rutas y contratos tecnicos se alinean a `/v1/workspaces` y a la entidad Workspace. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)
- La UI mantiene el termino "Seccion" sin cambiar el contrato tecnico. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)

## Impacto FE/BE/DB

- FE: navegacion y copy con "Workspaces/Secciones" y selector de workspace. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)
- BE/API: endpoints `/v1/workspaces/...`. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)
- DB: entidad `workspaces` y atributos definidos para Workspace. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)

## Validacion

- `pnpm test:backend:unit` (Fuente: `docs/quality/testing.md`, "Unit tests (Docker, recomendado)")
- `pnpm -C apps/frontend test` (Fuente: `docs/quality/testing.md`, "Frontend (Jest)")
- `pnpm e2e` (ver `docs/quality/testing.md` y `tests/e2e/README.md`)
