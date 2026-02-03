# Production Hardening
Guía de hardening con evidencia directa en el backend.

## Fuente de verdad
- Validaciones de producción → `apps/backend/app/crosscutting/config.py` (`Settings._validate_production_security`).
- Security headers → `apps/backend/app/crosscutting/security.py`.
- Métricas protegidas → `apps/backend/app/api/main.py` y `apps/backend/app/worker/worker_server.py`.

## Checklist mínimo (backend)
- `APP_ENV=production` (habilita validaciones de seguridad en `Settings`).
- `JWT_SECRET` fuerte y no default.
- `JWT_COOKIE_SECURE=true`.
- `METRICS_REQUIRE_AUTH=true`.
- `API_KEYS_CONFIG` o `RBAC_CONFIG` configurado (requerido en prod para `/metrics`).
- `GOOGLE_API_KEY` configurado o fakes habilitados (`FAKE_LLM=1` y `FAKE_EMBEDDINGS=1`).

## Headers de seguridad
`SecurityHeadersMiddleware` agrega:
- `Content-Security-Policy` (estricto en prod).
- `X-Frame-Options: DENY`.
- `X-Content-Type-Options: nosniff`.
- `Referrer-Policy: strict-origin-when-cross-origin`.
- `Permissions-Policy` restrictiva.
- `Strict-Transport-Security` cuando `x-forwarded-proto=https`.

Evidencia: `apps/backend/app/crosscutting/security.py`.

## Verificación rápida
```bash
# /metrics debe requerir X-API-Key si METRICS_REQUIRE_AUTH=true
curl -i <BASE_URL>/metrics
curl -i -H "X-API-Key: <KEY>" <BASE_URL>/metrics
```
