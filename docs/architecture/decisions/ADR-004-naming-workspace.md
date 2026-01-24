# ADR-004: Naming de Workspace (API/codigo) y Seccion (UI)

## Estado

**Aceptado** (2026-01-15) — Vigente en v6

## Contexto

- La especificacion **Especificación Base** define el naming tecnico: en codigo se usa Workspace, en UI se muestra Seccion, y la fuente de verdad tecnica es Workspace. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 7.1 Decision de naming")
- La API propuesta expone rutas bajo `/v1/workspaces`. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 13.2 Endpoints propuestos")
- La UI propuesta usa el label "Workspaces/Secciones" y un selector de workspace. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 14.1 Navegacion")

## Decision

- Usar **workspace** como termino tecnico en API/contratos/BE/DB; **seccion** queda solo como copy/label en UI. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 7.1 Decision de naming")
- Documentar el mapping UI -> workspace como convencion de producto para evitar drift entre capas. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 7.1 Decision de naming")

## Alternativas consideradas

1. "Seccion" en API/DB/codigo (descartado porque la decision **Especificación Base** fija Workspace como termino tecnico). (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 7.1 Decision de naming")
2. "Workspace" tambien en UI (descartado porque la **Especificación Base** permite Seccion en UI para ser natural en espanol). (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 7.1 Decision de naming")

## Consecuencias

- Las rutas y contratos tecnicos se alinean a `/v1/workspaces` y a la entidad Workspace. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 13.2 Endpoints propuestos", "### 7.2 Entidad Workspace")
- La UI mantiene el termino "Seccion" sin cambiar el contrato tecnico. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 7.1 Decision de naming", "### 14.1 Navegacion")

## Impacto FE/BE/DB

- FE: navegacion y copy con "Workspaces/Secciones" y selector de workspace. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 14.1 Navegacion")
- BE/API: endpoints `/v1/workspaces/...`. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 13.2 Endpoints propuestos")
- DB: entidad `workspaces` y atributos definidos para Workspace. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 12.2 Tablas nuevas", "### 7.2 Entidad Workspace")

## Validacion

- `pnpm test:backend:unit` (Fuente: `docs/quality/testing.md`, "Unit tests (Docker, recomendado)")
- `pnpm -C apps/frontend test` (Fuente: `docs/quality/testing.md`, "Frontend (Jest)")
- `pnpm e2e` (Fuente: `docs/quality/testing.md`, "Ejecutar E2E con apps/backend/frontend locales")
