# ADR-007: Compatibilidad de endpoints legacy vs nested workspaces

## Estado

**Aceptado** (2026-01-15) — Vigente en v6

## Contexto

- El baseline actual expone `/v1/documents`, `/v1/ask` y `/v1/ask/stream` en la API v1. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 5.2 Endpoints principales actuales")
- Las reglas **HISTORICAL v4** requieren que toda consulta incluya `workspace_id` y que el retrieval filtre por `workspace_id`. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 8.2 Reglas para consultas")
- La API **HISTORICAL v4** propone endpoints nested por workspace y permite mantener `/v1/documents` con `workspace_id` obligatorio; ademas recomienda rutas anidadas para evitar olvidar el scope. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 13.2 Endpoints propuestos")

## Decision

- Los endpoints canonicos son los nested bajo `/v1/workspaces/{id}/...` (documents, ask, ask/stream, query). (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 13.2 Endpoints propuestos")
- Los endpoints legacy `/v1/documents` y `/v1/ask` (incl. `/v1/ask/stream`) se mantienen temporalmente pero **requieren** `workspace_id` y quedan documentados como deprecated. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "GET /v1/workspaces/{id}/documents (o mantener /v1/documents con query workspace_id obligatorio)", "### 8.2 Reglas para consultas")
- No existe workspace implicito: si falta `workspace_id` en legacy, se rechaza la solicitud. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "1. Toda consulta debe incluir un workspace_id")

## Alternativas consideradas

1. Remover legacy de inmediato (descartado porque el baseline actual los expone). (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 5.2 Endpoints principales actuales")
2. Mantener legacy con workspace implicito (descartado por la regla **HISTORICAL v4** que exige `workspace_id`). (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "1. Toda consulta debe incluir un workspace_id")

## Consecuencias

- Los clientes actuales pueden migrar gradualmente, pero deben enviar `workspace_id` desde el inicio. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 8.2 Reglas para consultas", "### 13.2 Endpoints propuestos")
- Se evita drift de scope al preferir rutas nested para el uso futuro. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 13.2 Endpoints propuestos")

## Impacto FE/BE/DB

- FE: selector de workspace y envio de `workspace_id` en llamadas Ask/Docs. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 14.1 Navegacion", "### 8.2 Reglas para consultas")
- BE/API: implementar rutas nested y validar `workspace_id` en legacy. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 13.2 Endpoints propuestos", "### 8.2 Reglas para consultas")
- DB: `documents.workspace_id` obligatorio para scoping. (Fuente: `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md`, "### 12.3 Modificaciones a documents")

## Validacion

- `pnpm test:backend:unit` (Fuente: `doc/quality/testing.md`, "Unit tests (Docker, recomendado)")
- `pnpm -C frontend test` (Fuente: `doc/quality/testing.md`, "Frontend (Jest)")
- `pnpm e2e` (Fuente: `doc/quality/testing.md`, "Ejecutar E2E con backend/frontend locales")
