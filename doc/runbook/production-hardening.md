# Production Hardening (v6)

**Project:** RAG Corp
**Last Updated:** 2026-01-22

---

## Fail-fast (APP_ENV=production)

El backend valida requisitos de seguridad en `backend/app/config.py` y falla al iniciar si no se cumplen:

- `JWT_SECRET` fuerte (>= 32 chars) y no default
- `JWT_COOKIE_SECURE=true`
- `METRICS_REQUIRE_AUTH=true`
- `API_KEYS_CONFIG` o `RBAC_CONFIG` definido (protege `/metrics`)

---

## Headers de seguridad

Se aplican via `SecurityHeadersMiddleware` (`backend/app/security.py`):

- `Content-Security-Policy` sin `unsafe-inline` en produccion
- `Strict-Transport-Security`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy`
- `Permissions-Policy`

---

## Cookies

- JWT en cookie httpOnly (configurable via `JWT_COOKIE_NAME`)
- `JWT_COOKIE_SECURE=true` en prod
- `CORS_ALLOW_CREDENTIALS=false` por defecto

---

## /metrics protegido

- `METRICS_REQUIRE_AUTH=true` en prod
- API key debe incluir scope `metrics` o permiso RBAC `admin:metrics`

---

## Checklist de despliegue

1. `APP_ENV=production`
2. `JWT_SECRET` valido
3. `JWT_COOKIE_SECURE=true`
4. `METRICS_REQUIRE_AUTH=true`
5. `API_KEYS_CONFIG` o `RBAC_CONFIG`
6. `ALLOWED_ORIGINS` restringidos

