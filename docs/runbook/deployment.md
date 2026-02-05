<!--
===============================================================================
TARJETA CRC - docs/runbook/deployment.md
===============================================================================
Responsabilidades:
- Guiar el despliegue en entornos locales y productivos sin drift.
- Definir rutas preferidas (Helm) y alternativas (Kustomize) para K8s.
- Mantener comandos verificables y alineados a los nombres reales del runtime.

Colaboradores:
- infra/helm/ragcorp/README.md
- infra/k8s/overlays/*
- compose.yaml

Invariantes:
- No incluir secretos reales ni ejemplos sensibles.
- Los comandos deben referenciar servicios existentes (ej. rag-api, migrate).
===============================================================================
-->
# Deployment Guide

**Project:** RAG Corp  
**Last Updated:** 2026-02-05

---

## Overview

| Environment   | Método preferido | Config / Ruta |
| ------------- | ---------------- | ------------- |
| Development   | Docker Compose   | `compose.yaml` |
| Staging       | Helm (K8s)       | `infra/helm/ragcorp/examples/values-staging.yaml` |
| Production    | Helm (K8s)       | `infra/helm/ragcorp/examples/values-prod.yaml` |
| K8s (alterno) | Kustomize        | `infra/k8s/overlays/{staging,prod}/` |
| Observability | Docker Compose   | `compose.yaml --profile observability` |

**Nota:** Docker Compose es para **local** o **single-node demo**. Para producción, usar **Helm** (preferido) o **Kustomize overlays**.

---

## Variables requeridas (backend/worker)

- `DATABASE_URL`
- `GOOGLE_API_KEY`
- `JWT_SECRET`
- `JWT_COOKIE_SECURE=true`
- `API_KEYS_CONFIG` o `RBAC_CONFIG`
- `METRICS_REQUIRE_AUTH=true`

Plantillas:
- Local: `.env.example` → `.env` (no versionado)
- K8s: `infra/k8s/base/secret.yaml` es **solo plantilla** (no aplicar)

---

## Docker Compose (local / single-node demo)

```bash
# Crear env local (no versionado)
cp .env.example .env
# Editar .env con valores locales

# Stack base (DB + migrate + API)
pnpm stack:core

# Stack full (incluye UI + observabilidad)
pnpm stack:all
```

Migraciones manuales (si se requiere):

```bash
docker compose run --rm --no-deps migrate
```

Health checks:

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
```

---

## Kubernetes (producción)

### Opción preferida: Helm

```bash
# Staging
helm upgrade --install ragcorp infra/helm/ragcorp \
  -n ragcorp --create-namespace \
  -f infra/helm/ragcorp/examples/values-staging.yaml

# Production
helm upgrade --install ragcorp infra/helm/ragcorp \
  -n ragcorp --create-namespace \
  -f infra/helm/ragcorp/examples/values-prod.yaml
```

### Opción alternativa: Kustomize overlays

```bash
# Staging
kubectl apply -k infra/k8s/overlays/staging

# Production
kubectl apply -k infra/k8s/overlays/prod
```

### Política de imágenes (prod)

- Usar **tags inmutables** (`sha-<gitsha>` o semver) en overlays.
- **No** usar `latest` en producción.

### Verificar overlays sin kubectl (dockerizado)

```bash
bash infra/k8s/render_kustomize.sh staging --out /tmp/ragcorp-staging.yaml
bash infra/k8s/render_kustomize.sh prod --out /tmp/ragcorp-prod.yaml

# Verificar que prod NO contiene :latest
rg ':latest' /tmp/ragcorp-prod.yaml
```

---

## Observability (local)

```bash
docker compose --profile observability up -d
```

URLs:

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001

---

## GitHub Actions / CI/CD

El workflow de deploy usa GitHub Environments (`staging` y `production`).

### Variables Required (GitHub Secrets/Vars)

| Variable             | Descripción                                 |
| -------------------- | ------------------------------------------- |
| `PROD_BASE_URL`      | Base URL para health checks en prod         |
| `PROD_SMOKE_PATH`    | Path para smoke test (opcional)             |
| `PROD_SMOKE_API_KEY` | Header X-API-Key para smoke test (opcional) |

### Rollback

- **Helm**: `helm rollback <release> <revision> -n <namespace>`
- **Kubernetes**: `kubectl rollout undo deployment/<name>`
- **Docker Compose**: `docker compose pull <prev-tag> && docker compose up -d`
