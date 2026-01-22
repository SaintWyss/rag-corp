# Deploy Runbook (v6)

Este runbook describe la configuracion minima para que el workflow `Deploy` ejecute health checks y smoke tests de forma segura (gated).

## Variables y secrets (GitHub Environments)

Configurar en los environments `staging` y `production`:

Variables (vars):
- `STAGING_BASE_URL` (solo en environment staging)
- `PROD_BASE_URL` (solo en environment production)
- `STAGING_SMOKE_PATH` (opcional, solo staging)
- `PROD_SMOKE_PATH` (opcional, solo production)

Secrets:
- `STAGING_SMOKE_API_KEY` (opcional, solo staging)
- `PROD_SMOKE_API_KEY` (opcional, solo production)

Notas:
- Los health checks se ejecutan solo si existe `*_BASE_URL`.
- Los smoke tests se ejecutan solo si existen ambos `*_SMOKE_PATH` y `*_SMOKE_API_KEY`.
- El workflow no hace curl contra URLs ejemplo.

## Required env in production

| Nombre | Componente | Por qué es required | Ejemplo seguro (placeholder) |
| --- | --- | --- | --- |
| `APP_ENV` | backend/worker | Activa `is_production()` para hardening y CSP estricto | `production` |
| `JWT_SECRET` | backend/worker | Firma de JWT; validado fuerte en prod | `replace-with-32+char-secret` |
| `JWT_COOKIE_SECURE` | backend/worker | Requerido `true` en prod para cookies `Secure` | `true` |
| `METRICS_REQUIRE_AUTH` | backend/worker | Requerido `true` en prod para proteger `/metrics` | `true` |
| `API_KEYS_CONFIG` | backend/worker | Requerido si no hay `RBAC_CONFIG` para auth de métricas | `{"example-key":["metrics:read"]}` |
| `RBAC_CONFIG` | backend/worker | Alternativa a `API_KEYS_CONFIG` para RBAC | `{"roles":{},"key_roles":{}}` |
| `ALLOWED_ORIGINS` | backend | CORS: evita default local en prod | `https://app.example.com` |
| `CORS_ALLOW_CREDENTIALS` | backend | CORS: habilita cookies cross-origin solo si aplica | `false` |

Para Docker Compose prod, inyectar estas variables desde el entorno o un env-file externo (ej: `docker compose --env-file /path/.env.prod -f compose.prod.yaml up -d`). No commitear secretos.

## Endpoints verificados

Health checks (si hay `*_BASE_URL`):
- `GET /healthz`
- `GET /readyz`

Smoke test (si hay `*_SMOKE_PATH` + `*_SMOKE_API_KEY`):
- `GET /<SMOKE_PATH>` con header `X-API-Key`

`*_SMOKE_PATH` debe apuntar a un endpoint GET protegido que responda 2xx.

## Como configurar los environments

1) Abrir Settings del repo y entrar a Environments.
2) En `staging`, agregar `STAGING_BASE_URL` y, si aplica, `STAGING_SMOKE_PATH` + `STAGING_SMOKE_API_KEY`.
3) En `production`, agregar `PROD_BASE_URL` y, si aplica, `PROD_SMOKE_PATH` + `PROD_SMOKE_API_KEY`.

## Rollback

El workflow incluye un job `rollback` con comandos de ejemplo. Ajustar segun el metodo real de despliegue:
- Kubernetes: `kubectl rollout undo deployment/<name>`
- Docker Compose: `docker compose -f compose.prod.yaml pull <previous-tag> && docker compose -f compose.prod.yaml up -d`

Ver `doc/runbook/deployment.md` para el flujo general de despliegue.
