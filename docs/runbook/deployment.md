# Deployment Guide (v6)

**Project:** RAG Corp
**Last Updated:** 2026-01-22

---

## Overview

| Environment   | Method                 | Config                                      |
| ------------- | ---------------------- | ------------------------------------------- |
| Development   | Docker Compose         | `compose.yaml`                              |
| Production    | Docker Compose         | `compose.prod.yaml`                         |
| Observability | Docker Compose profile | `compose.prod.yaml --profile observability` |

---

## Required Variables (prod)

- `DATABASE_URL`
- `GOOGLE_API_KEY`
- `JWT_SECRET`
- `JWT_COOKIE_SECURE=true`
- `API_KEYS_CONFIG` o `RBAC_CONFIG`
- `METRICS_REQUIRE_AUTH=true`

Ver `.env.example` para el listado completo.

---

## Docker Compose (production)

```bash
cp .env.example .env.prod
# Edit .env.prod

docker compose -f compose.prod.yaml --env-file .env.prod build
docker compose -f compose.prod.yaml --env-file .env.prod up -d
```

El servicio `backend` ejecuta `alembic upgrade head` al iniciar.
Si se requiere, se puede correr manualmente:

```bash
docker compose -f compose.prod.yaml exec backend alembic upgrade head
```

Health checks:

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
```

---

## Observability (prod)

```bash
docker compose -f compose.prod.yaml --profile observability up -d
```

URLs:

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001

---

## Kubernetes

Ver `infra/k8s/README.md` y `docs/runbook/kubernetes.md`.

## GitHub Actions / CI/CD (Legacy deploy.md info)

El workflow de deploy usa GitHub Environments (`staging` y `production`).

### Variables Required (GitHub Secrets/Vars)

| Variable             | Descripción                                 |
| -------------------- | ------------------------------------------- |
| `PROD_BASE_URL`      | Base URL para health checks en prod         |
| `PROD_SMOKE_PATH`    | Path para smoke test (opcional)             |
| `PROD_SMOKE_API_KEY` | Header X-API-Key para smoke test (opcional) |

### Rollback

- **Kubernetes**: `kubectl rollout undo deployment/<name>`
- **Docker Compose**: `docker compose pull <prev-tag> && docker compose up -d`
