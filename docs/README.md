# Documentacion RAG Corp v6

**Last Updated:** 2026-01-22

Este directorio contiene la documentacion tecnica vigente de RAG Corp v6. El portal de entrada es `../README.md`.
Las referencias a v4 se consideran **HISTORICAL** y solo se mantienen como origen/traceabilidad.

## Indice principal

- `../README.md` - Portal v6 (quickstart + links)
- `architecture/overview.md` - Arquitectura, capas y flujos
- `architecture/decisions/` - ADRs vigentes (v6) con notas historicas si aplica
- `api/http-api.md` - API HTTP y ejemplos
- `api/rbac.md` - RBAC para API keys
- `data/postgres-schema.md` - Schema y indices PostgreSQL
- `runbook/local-dev.md` - Desarrollo local
- `runbook/migrations.md` - Migraciones (Alembic)
- `runbook/production-hardening.md` - Hardening prod (fail-fast, CSP, /metrics)
- `runbook/observability.md` - Observabilidad (health/ready/metrics, perfiles compose)
- `runbook/troubleshooting.md` - Troubleshooting operativo
- `quality/testing.md` - Estrategia de testing
- `../tests/e2e/README.md` - Playwright E2E
- `../apps/backend/tests/README.md` - Tests backend
- `../shared/contracts/openapi.json` - OpenAPI (fuente de verdad)

## Mantenimiento

- Mantener consistencia con `shared/contracts/openapi.json`, `apps/backend/alembic/` y `compose*.yaml`.
- Si cambian endpoints, schema o env vars, actualizar docs en el mismo cambio.
- Referencias historicas deben etiquetarse como **HISTORICAL**.

## Resumen v6

RAG Corp v6 es un sistema RAG workspace-first con scoping estricto por `workspace_id` y gobernanza por visibilidad (`PRIVATE | ORG_READ | SHARED`) + `workspace_acl`.
Los endpoints canonicos viven bajo `/v1/workspaces/{workspace_id}/...` y los legacy se documentan como `DEPRECATED`.

## Operacion y calidad

- **Observabilidad**: `/healthz`, `/readyz`, `/metrics` (auth en prod) + perfiles compose.
- **Seguridad**: JWT + API keys con RBAC opcional; hardening en `APP_ENV=production`.
- **Testing**: unit + e2e + e2e-full (ver `docs/quality/testing.md`).

## Historico (HISTORICAL)

- `docs/hitos/` (specs y reportes HISTORICAL v4)
- `docs/audits/` y `docs/reviews/` (auditorias internas)
- `docs/archive/` (logs y reportes historicos consolidados)
