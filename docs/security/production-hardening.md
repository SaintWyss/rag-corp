# Production hardening (seguridad)
Este documento resume hardening del backend con evidencia en código.

## Fuente de verdad
- Validaciones de producción → `apps/backend/app/crosscutting/config.py`.
- Security headers → `apps/backend/app/crosscutting/security.py`.
- /metrics protegido → `apps/backend/app/api/main.py` y `apps/backend/app/worker/worker_server.py`.

## Checklist mínimo
- `APP_ENV=production`.
- `JWT_SECRET` fuerte y no default.
- `JWT_COOKIE_SECURE=true`.
- `METRICS_REQUIRE_AUTH=true`.
- `API_KEYS_CONFIG` o `RBAC_CONFIG` configurado.

## Ver también
- Runbook operativo → `../runbook/production-hardening.md`
