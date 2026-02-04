# ADR-007: Workspace-Scoped Endpoints

## Estado

**Aceptado** (2026-01-15) — Vigente

## Contexto

- Todas las operaciones de documentos y RAG deben estar **scoped** por `workspace_id`.
- El scoping evita mezcla de fuentes y simplifica la gobernanza.
- El contrato HTTP debe reflejar el contexto de workspace de manera explícita.

## Decisión

- Se exponen **solo** endpoints workspace-scoped bajo `/v1/workspaces/{workspace_id}/...`.
- No se publican rutas globales para documentos/ask/query/ingest.
- El `workspace_id` se resuelve siempre desde el path y se valida en el borde.

## Consecuencias

- FE opera siempre dentro de un workspace (selector obligatorio).
- BE aplica scoping obligatorio en repositorios/use cases.
- OpenAPI refleja únicamente rutas workspace-scoped.

## Impacto FE/BE/DB

- FE: navegación y requests bajo `/workspaces/{id}/...` y `/v1/workspaces/{id}/...`.
- BE/API: routers en `/v1/workspaces/{id}/...`.
- DB: `documents.workspace_id` obligatorio y filtrado en retrieval.

## Validación

- Unit tests: policy + use cases scoped.
- Integration tests: ask/query/ingest con `workspace_id` en path.
- E2E: flujo completo workspace-scoped.
