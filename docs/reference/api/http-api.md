# HTTP API (guía transversal)
Fuente de verdad del contrato: `shared/contracts/openapi.json` (exportado desde `apps/backend/scripts/export_openapi.py`).

## Prefijos y versionado
- Prefijo canónico de negocio: `/v1` (router raíz incluido en `apps/backend/app/api/main.py`).
- Alias de compatibilidad: `/api/v1` (ver `apps/backend/app/api/versioning.py`).

## OpenAPI
- Archivo exportado: `shared/contracts/openapi.json`.
- Script de export: `apps/backend/scripts/export_openapi.py`.

Ejemplo de export:
```bash
cd apps/backend
python scripts/export_openapi.py --out ../shared/contracts/openapi.json
```

## Endpoints operativos (HTTP)
Definidos en `apps/backend/app/api/main.py`:
- `/healthz`
- `/readyz`
- `/metrics` (protegido por `require_metrics_permission` si `METRICS_REQUIRE_AUTH=1`).

## Autenticación (resumen)
- API key: header `X-API-Key` (`apps/backend/app/identity/auth.py`).
- JWT (usuarios): roles `admin`/`employee` en `apps/backend/app/identity/users.py`.
- Ver detalle en `docs/reference/access-control.md`.

## Endpoints de negocio
Para evitar drift, **no** duplicamos endpoints específicos en este documento. Usar:
- OpenAPI → `shared/contracts/openapi.json`
- Routers HTTP → `apps/backend/app/interfaces/api/http/routers/`
