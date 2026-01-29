# Repo cleanup v6 runbook

Fecha: 2026-01-29

## FASE 1 — Inventario (solo lectura)

### Candidatos basura trackeados
- Resultado `git ls-files | rg ...` (caches/build/logs/etc): 0 matches.
- Archivos >1MB trackeados: 0 matches.

### Candidatos legacy
- `docs/architecture/decisions/ADR-006-archive-soft-delete.md`
- `docs/architecture/decisions/ADR-007-legacy-endpoints.md`

## Evidencia de no-uso (previo a borrar)
- `rg -n "ADR-006-archive-soft-delete" .` -> 1 match en `docs/README.md`.
- `rg -n "ADR-007-legacy-endpoints" .` -> 1+ matches en `docs/README.md` y `docs/architecture/decisions/ADR-007-legacy-endpoints.md`.

## TODOs dudosos
- Referencias en `docs/architecture/decisions/ADR-007-legacy-endpoints.md` a `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md` no se encontraron en el repo; no se tocó por ser contenido contractual.

## FASE 2 — Plan (máx 10 bullets)
1) Confirmar que no hay basura trackeada para borrar.
2) Reforzar `.gitignore` con patrones de cookies y artifacts faltantes.
3) Agregar `.dockerignore` raíz mínimo si falta.
4) No borrar legacy con referencias activas (documentar decisión).
5) Correr checks mínimos solicitados y reportar resultados.

## FASE 3 — Ejecución
- No hubo `git rm` (sin basura trackeada ni legacy sin referencias).
- Actualicé `.gitignore` para incluir `cookies*.txt`.
- Agregué `.dockerignore` raíz mínimo.

## FASE 4 — Validación
- Backend:
  - `cd apps/backend && ruff check .` -> OK.
  - `cd apps/backend && ruff format --check .` -> reformat requerido; ejecutado `ruff format .` y luego OK.
  - `cd apps/backend && pytest -q` -> OK (388 passed, 2 skipped).
- Frontend:
  - `cd apps/frontend && pnpm install --frozen-lockfile` -> OK.
  - `cd apps/frontend && pnpm lint` -> OK (se removió un eslint-disable no usado en `safeNext.ts`).
  - `cd apps/frontend && pnpm tsc --noEmit` -> FAIL (módulos no encontrados en `__tests__/*` y `@ts-expect-error` unused).
- Contracts:
  - `pnpm contracts:gen` -> OK.
  - `git diff --exit-code shared/contracts/` -> OK (sin cambios).
- E2E:
  - `pnpm -C tests/e2e test` -> FAIL (webServer no inicia; falta `database_url` en Settings).

## FASE 5 — Resultado final
- ⚠️ Estado: validación incompleta (falló `pnpm tsc --noEmit` y E2E por falta de `database_url`).

### Archivos tocados (este cleanup)
- `.gitignore`
- `.dockerignore`
- `docs/runbook/repo-cleanup-v6.md`
- `apps/backend/app/api/admin_routes.py`
- `apps/backend/app/api/main.py`
- `apps/backend/app/application/dev_seed_demo.py`
- `apps/backend/app/identity/dual_auth.py`
- `apps/backend/app/infrastructure/repositories/postgres_user_repo.py`
- `apps/backend/app/infrastructure/services/cached_embedding_service.py`
- `apps/backend/tests/conftest.py`
- `apps/backend/tests/unit/test_admin_workspace_provisioning.py`
- `apps/backend/tests/unit/test_dev_seed_admin.py`
- `apps/backend/tests/unit/test_dual_authz.py`
- `apps/backend/tests/unit/test_jobs.py`
- `apps/backend/tests/unit/test_observability.py`
- `apps/backend/tests/unit/test_rfc7807_errors.py`
- `apps/backend/tests/unit/test_upload_endpoint.py`
- `apps/backend/tests/unit/test_user_auth.py`
- `apps/frontend/src/shared/lib/safeNext.ts`

### Resumen (≤10 bullets)
- No se encontró basura trackeada ni legacy sin referencias para borrar.
- Se reforzó `.gitignore` para `cookies*.txt`.
- Se agregó `.dockerignore` raíz mínimo.
- Se removió un `eslint-disable` innecesario en frontend.
- Se removieron imports/variables no usados y se añadió `# noqa: E402` para imports deliberados fuera de orden.
- Se aplicó `ruff format` a backend/tests (solo formato).
- Checks backend OK; frontend tsc y E2E fallaron por razones externas a este cambio.

### Eliminado + evidencia
- Nada eliminado (sin candidatos sin referencias).

### Comandos corridos + resultado (resumen)
- `git ls-files | rg ...` -> 0 matches (basura trackeada).
- `git ls-files -z | ... | awk '$1>1000000'` -> 0 matches (>1MB).
- `rg -n "ADR-006-archive-soft-delete" .` -> 1 match en `docs/README.md`.
- `rg -n "ADR-007-legacy-endpoints" .` -> matches en docs.
- `cd apps/backend && ruff check .` -> OK.
- `cd apps/backend && ruff format --check .` -> requería formato; luego OK con `ruff format .`.
- `cd apps/backend && pytest -q` -> OK.
- `cd apps/frontend && pnpm install --frozen-lockfile` -> OK.
- `cd apps/frontend && pnpm lint` -> OK.
- `cd apps/frontend && pnpm tsc --noEmit` -> FAIL (módulos no encontrados en `__tests__/*`).
- `pnpm contracts:gen` -> OK.
- `git diff --exit-code shared/contracts/` -> OK.
- `pnpm -C tests/e2e test` -> FAIL (webServer no inicia; falta `database_url`).

### TODOs que quedaron
- Revisar referencia a `.github/informe_de_producto_y_analisis_rag_corp_v_4_workspaces_secciones_gobernanza_y_roadmap.md` (no existe en repo).
