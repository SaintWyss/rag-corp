# Control de acceso
Fuente de verdad: `apps/backend/app/identity/` y `apps/backend/app/crosscutting/config.py`.

## Mecanismos soportados
- **API Keys** (`X-API-Key`) con scopes en `apps/backend/app/identity/auth.py`.
- **RBAC para API Keys** (roles + permisos) en `apps/backend/app/identity/rbac.py`.
- **JWT para usuarios** (roles `admin`/`employee`) en `apps/backend/app/identity/users.py` y `apps/backend/app/identity/auth_users.py`.
- **Principal unificado (USER/SERVICE)** en `apps/backend/app/identity/dual_auth.py`.

## API Keys (scopes)
- Configuración: `API_KEYS_CONFIG` (JSON) leído en `apps/backend/app/identity/auth.py`.
- Scopes disponibles y su mapeo a permisos: `SCOPE_PERMISSIONS` en `apps/backend/app/identity/rbac.py`.
- Si no hay `API_KEYS_CONFIG` ni `RBAC_CONFIG`, la autenticación por API key se considera deshabilitada (ver `require_permissions` en `apps/backend/app/identity/rbac.py` y `require_scope` en `apps/backend/app/identity/auth.py`).

## RBAC (roles + permisos)
- Configuración: `RBAC_CONFIG` (JSON) leído en `apps/backend/app/identity/rbac.py`.
- Permisos disponibles: `Permission` en `apps/backend/app/identity/rbac.py`.
- Roles default: `DEFAULT_ROLES` en `apps/backend/app/identity/rbac.py`.
- Validación de producción: `Settings._validate_production_security()` en `apps/backend/app/crosscutting/config.py` exige `API_KEYS_CONFIG` o `RBAC_CONFIG` para proteger `/metrics`.

## JWT (usuarios)
- Roles de usuario (`admin`, `employee`) definidos en `apps/backend/app/identity/users.py`.
- Extracción/validación de token en `apps/backend/app/identity/auth_users.py`.
- Dependencias FastAPI para roles en `apps/backend/app/identity/dual_auth.py` (`require_admin`, `require_employee_or_admin`, `require_user_roles`).

## Policy de acceso a documentos
- La policy de acceso a documentos vive en `apps/backend/app/identity/access_control.py` (`can_access_document`, `filter_documents`).
- Esta policy es lógica pura, sin dependencias de FastAPI.

## Dónde se aplica
- Routers HTTP usan dependencias de `identity/*` (ver `apps/backend/app/interfaces/api/http/routers/`).
- `/metrics` puede requerir permisos según `metrics_require_auth` en `apps/backend/app/crosscutting/config.py` y `require_metrics_permission` en `apps/backend/app/identity/rbac.py`.
