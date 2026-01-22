---
applyTo: "doc/**"
---

# Docs — reglas específicas del repo (v6)

## Estado / Versión (v6)
- La documentación vigente del proyecto es **v6**.
- “v4” solo puede aparecer como **HISTORICAL** (origen/especificación pasada), claramente marcado.

## Modo de trabajo
- Ejecutar cambios directamente (sin pedir confirmación), salvo: ambigüedad bloqueante, cambio destructivo, o riesgo de seguridad.
- No pegar archivos completos: entregar **diff/patch** + **archivos tocados** + **resumen (≤10 bullets)** + **comandos de validación**.

## Source of Truth (anti-drift)
Antes de afirmar algo “como cierto” en docs (endpoints, comandos, services, tablas, scripts), verificar en este orden:
1) **Informe de Sistemas v6 (Definitivo)** (`doc/system/...`) si existe.
2) **Contracts**: `shared/contracts/openapi.json` (y client generado si aplica).
3) **DB/Migraciones**: `backend/alembic/versions/*` + `doc/data/postgres-schema.md`.
4) **Runtime real**: `compose*.yaml`, `package.json`, CI workflows, `frontend/next.config.ts`, `backend/app/main.py`/`routes.py`.
5) **Decisiones**: `doc/architecture/decisions/ADR-*.md`.

## Veracidad / No alucinaciones
- No inventar features/endpoints/comandos. Si algo no existe en el repo, marcarlo como **TODO/Planned**.
- Verificar siempre contra:
  - API: `shared/contracts/openapi.json` (primario) y luego `backend/app/routes.py`, `backend/app/main.py`.
  - Docker/Infra: `compose*.yaml` (incluye prod/observability si existen).
  - Scripts: `package.json` (root y workspaces relevantes).
  - DB: `backend/alembic/versions/*` (primario) + `doc/data/postgres-schema.md`.

## Índices y rutas canónicas
- `doc/README.md` es el índice principal (mantener links vivos).
- `README.md` raíz debe apuntar a `doc/README.md` (portal).
- Documentos “fuente”:
  - Arquitectura: `doc/architecture/overview.md`
  - API HTTP: `doc/api/http-api.md`
  - Data/schema: `doc/data/postgres-schema.md`
  - Runbook local: `doc/runbook/local-dev.md`

## Convenciones de comandos (este repo)
- Usar `docker compose` (no `docker-compose`).
- Nunca asumir services: listar los **services reales** leyendo `compose.yaml` (y `compose.*.yaml` si aplican) antes de documentarlos.
- Si mencionás generación de contratos, usar los scripts reales del repo (verificar en `package.json`):
  - `pnpm contracts:export`
  - `pnpm contracts:gen`

## Regla v6 (si aplica): workspaces + scoping
- Si la documentación describe documentos/chat/RAG, debe reflejar scoping por `workspace_id` si existe en v6.
- Endpoints canónicos (si existen): `/v1/workspaces/{id}/...`
- Endpoints legacy (si existen): **DEPRECATED** y siempre con `workspace_id` explícito (nunca implícito).

## Regla de actualización
- Si un cambio toca API, DB, contracts o compose:
  - actualizar docs correspondientes en el mismo **commit**.

## Comandos de validación (cuando aplique)
- Links y rutas: revisar que los paths existan.
- API examples (ajustar a lo que exista en OpenAPI):
  - `curl http://localhost:8000/healthz`
  - `curl http://localhost:8000/readyz`
  - Si existen endpoints de ask/chat: usar ejemplos que incluyan `workspace_id` cuando aplique.