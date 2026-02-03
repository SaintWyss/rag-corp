# ADR-009: Separación Admin vs Employee

## Status
Accepted

## Contexto
El backend define roles de usuario `admin` y `employee` (`apps/backend/app/identity/users.py`).

## Decisión
La separación de permisos se aplica en el borde HTTP mediante dependencias de rol:
- `require_admin()` / `require_employee_or_admin()` en `apps/backend/app/identity/dual_auth.py`.
- Uso de estas dependencias en routers: `apps/backend/app/interfaces/api/http/routers/workspaces.py` y `routers/admin.py`.

## Consecuencias
- Las rutas que exigen rol se controlan en el nivel de router (FastAPI) con dependencias explícitas.
- El detalle de permisos por endpoint se mantiene en OpenAPI (`shared/contracts/openapi.json`) y en los routers actuales.

## OBSOLETO (no verificado)
Los detalles previos sobre rutas frontend y matrices por endpoint quedaron desactualizados. Ver:
- Routers actuales → `apps/backend/app/interfaces/api/http/routers/`
- OpenAPI → `shared/contracts/openapi.json`
