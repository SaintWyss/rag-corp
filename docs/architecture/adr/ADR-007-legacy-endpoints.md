# ADR-007: Compatibilidad de endpoints legacy vs nested workspaces

## Estado

**Aceptado** (2026-01-15) — Vigente en v6

## Contexto

- El baseline actual expone `/v1/documents`, `/v1/ask` y `/v1/ask/stream` en la API v1. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)
- Las reglas **Especificación Base** requieren que toda consulta incluya `workspace_id` y que el retrieval filtre por `workspace_id`. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)
- La API **Especificación Base** propone endpoints nested por workspace y permite mantener `/v1/documents` con `workspace_id` obligatorio; ademas recomienda rutas anidadas para evitar olvidar el scope. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)

## Decision

- Los endpoints canonicos son los nested bajo `/v1/workspaces/{id}/...` (documents, ask, ask/stream, query). (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)
- Los endpoints legacy `/v1/documents` y `/v1/ask` (incl. `/v1/ask/stream`) se mantienen temporalmente pero **requieren** `workspace_id` y quedan documentados como deprecated. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)
- No existe workspace implicito: si falta `workspace_id` en legacy, se rechaza la solicitud. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)

## Alternativas consideradas

1. Remover legacy de inmediato (descartado porque el baseline actual los expone). (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)
2. Mantener legacy con workspace implicito (descartado por la regla **Especificación Base** que exige `workspace_id`). (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)

## Consecuencias

- Los clientes actuales pueden migrar gradualmente, pero deben enviar `workspace_id` desde el inicio. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)
- Se evita drift de scope al preferir rutas nested para el uso futuro. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)

## Impacto FE/BE/DB

- FE: selector de workspace y envio de `workspace_id` en llamadas Ask/Docs. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)
- BE/API: implementar rutas nested y validar `workspace_id` en legacy. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)
- DB: `documents.workspace_id` obligatorio para scoping. (Fuente: `TODO(verify: missing .github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md)`)

## Validacion

- `pnpm test:backend:unit` (Fuente: `docs/quality/testing.md`, "Unit tests (Docker, recomendado)")
- `pnpm -C apps/frontend test` (Fuente: `docs/quality/testing.md`, "Frontend (Jest)")
- `pnpm e2e` (Fuente: `docs/quality/testing.md`, "Ejecutar E2E con apps/backend/frontend locales")
