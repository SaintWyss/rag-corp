---
applyTo: "docs/**"
---

# Docs — reglas específicas del repo

## Estado / Versión

- Baseline actual: `docs/project/informe_de_sistemas_rag_corp.md`.
- No usar etiquetas internas de versión en documentación.

## Modo de trabajo

- Ejecutar cambios directamente (sin pedir confirmación), salvo: ambigüedad bloqueante, cambio destructivo, o riesgo de seguridad.
- No pegar archivos completos: entregar **diff/patch** + **archivos tocados** + **resumen (≤10 bullets)** + **comandos de validación**.

## Source of Truth (anti-drift)

Antes de afirmar algo “como cierto” en docs (endpoints, comandos, services, tablas, scripts), verificar en este orden:

1. **Informe de Sistemas (Definitivo)**: `docs/project/informe_de_sistemas_rag_corp.md`.
2. **Contracts**: `shared/contracts/openapi.json` (y client generado si aplica).
3. **DB/Migraciones**: `apps/backend/alembic/versions/*` + `docs/reference/data/postgres-schema.md`.
4. **Runtime real**: `compose*.yaml`, `package.json`, CI workflows, `apps/frontend/next.config.mjs`, `apps/backend/app/main.py`, `apps/backend/app/api/main.py`, `apps/backend/app/interfaces/api/http/routes.py`.
5. **Decisiones**: `docs/architecture/adr/ADR-*.md`.

## Veracidad / No alucinaciones

- No inventar features/endpoints/comandos. Si algo no existe en el repo, marcarlo como **TODO/Planned**.
- Verificar siempre contra:
  - API: `shared/contracts/openapi.json` (primario) y luego `apps/backend/app/interfaces/api/http/routes.py`, `apps/backend/app/api/main.py`.
  - Docker/Infra: `compose*.yaml` (incluye prod/observability si existen).
  - Scripts: `package.json` (root y workspaces relevantes).
  - DB: `apps/backend/alembic/versions/*` (primario) + `docs/reference/data/postgres-schema.md`.

## Índices y rutas canónicas

- `docs/README.md` es el índice principal (mantener links vivos).
- `README.md` raíz debe apuntar a `docs/README.md` (portal).
- Documentos “fuente”:
  - Arquitectura: `docs/architecture/overview.md`
  - API HTTP: `docs/reference/api/http-api.md`
  - Data/schema: `docs/reference/data/postgres-schema.md`
  - Runbook local: `docs/runbook/local-dev.md`

## Convenciones de comandos (este repo)

- Usar `docker compose` (no `docker-compose`).
- Nunca asumir services: listar los **services reales** leyendo `compose.yaml` (y `compose.*.yaml` si aplican) antes de documentarlos.
- Si mencionás generación de contratos, usar los scripts reales del repo (verificar en `package.json`):
  - `pnpm contracts:export`
  - `pnpm contracts:gen`

## Regla de workspaces + scoping

- Si la documentación describe documentos/chat/RAG, debe reflejar scoping por `workspace_id`.
- Endpoints canónicos: `/v1/workspaces/{id}/...`

## Regla de actualización

- Si un cambio toca API, DB, contracts o compose:
  - actualizar docs correspondientes en el mismo **commit**.

## Comandos de validación (cuando aplique)

- Links y rutas: revisar que los paths existan.
- API examples (ajustar a lo que exista en OpenAPI):
  - `curl http://localhost:8000/healthz`
  - `curl http://localhost:8000/readyz`
  - Si existen endpoints de ask/chat: usar ejemplos que incluyan `workspace_id` cuando aplique.
