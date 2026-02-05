<!--
===============================================================================
TARJETA CRC - docs/runbook/kubernetes.md
===============================================================================
Responsabilidades:
- Documentar el despliegue en Kubernetes con Helm (preferido) y Kustomize (alterno).
- Mantener comandos verificables y coherentes con los manifiestos reales.

Colaboradores:
- infra/helm/ragcorp/README.md
- infra/k8s/overlays/*
- infra/k8s/README.md

Invariantes:
- No incluir secretos reales.
- Referenciar rutas existentes del repo.
===============================================================================
-->
# Kubernetes Deployment Guide

**Project:** RAG Corp  
**Last Updated:** 2026-01-22

---

## Overview

**Preferido:** Helm chart en `infra/helm/ragcorp/`.  
**Alternativo:** Kustomize overlays en `infra/k8s/overlays/{staging,prod}/`.

RAG Corp mantiene manifests base en [`infra/k8s/`](../../infra/k8s/).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐       │
│  │   Ingress   │   │   Ingress   │   │  Prometheus │       │
│  │ (Frontend)  │   │   (API)     │   │   Scraper   │       │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘       │
│         │                 │                 │               │
│         ▼                 ▼                 ▼               │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐       │
│  │  Frontend   │   │   Backend   │   │    Redis    │       │
│  │  (2 pods)   │──▶│  (2-10 pods)│──▶│  (1 pod)    │       │
│  │  HPA: N/A   │   │  HPA: CPU   │   │             │       │
│  └─────────────┘   └──────┬──────┘   └─────────────┘       │
│                          │                                  │
│                          ▼                                  │
│                   ┌─────────────┐                           │
│                   │  PostgreSQL │                           │
│                   │  (external) │                           │
│                   └─────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start (preferido: Helm)

```bash
# Staging
helm upgrade --install ragcorp infra/helm/ragcorp \\
  -n ragcorp --create-namespace \\
  -f infra/helm/ragcorp/examples/values-staging.yaml

# Production
helm upgrade --install ragcorp infra/helm/ragcorp \\
  -n ragcorp --create-namespace \\
  -f infra/helm/ragcorp/examples/values-prod.yaml
```

## Quick Start (alterno: Kustomize overlays)

```bash
# 1. Apply overlay (staging o prod)
kubectl apply -k infra/k8s/overlays/staging

# 2. Verify deployment
kubectl -n ragcorp get pods -w

# 3. Check services
kubectl -n ragcorp get svc
```

## Verificación de overlays sin kubectl

```bash
bash scripts/ops/render_kustomize.sh staging > /tmp/staging.yaml
bash scripts/ops/render_kustomize.sh prod > /tmp/prod.yaml

# En producción no debe existir :latest
rg ':latest' /tmp/prod.yaml
```

## Manifests

| File | Description |
|------|-------------|
| `namespace.yaml` | Dedicated namespace `ragcorp` |
| `configmap.yaml` | Non-sensitive configuration |
| `secret.yaml` | Sensitive data (DB URL, API keys) |
| `backend-deployment.yaml` | FastAPI backend with security contexts |
| `backend-service.yaml` | Backend ClusterIP service |
| `backend-hpa.yaml` | Horizontal Pod Autoscaler (2-10 pods) |
| `frontend-deployment.yaml` | Next.js frontend |
| `frontend-service.yaml` | Frontend ClusterIP service |
| `ingress.yaml` | NGINX Ingress with TLS |
| `redis-deployment.yaml` | Redis cache |
| `pdb.yaml` | Pod Disruption Budgets |
| `network-policy.yaml` | Zero-trust network policies |

## Security Features

### Container Security

- Non-root execution (`runAsNonRoot: true`)
- Read-only root filesystem
- Dropped capabilities
- No privilege escalation

### Network Security

- Zero-trust network policies (deny-all default)
- Explicit ingress/egress rules per component
- TLS termination at ingress

### Secrets Management

```bash
# Generate base64 secrets
echo -n "postgresql://user:pass@host:5432/db" | base64

# For production, use External Secrets Operator
# See secret.yaml for example configuration
```

## Scaling

### Horizontal Pod Autoscaler

Backend scales automatically based on:
- CPU utilization (target: 70%)
- Memory utilization (target: 80%)

```bash
# Check HPA status
kubectl -n ragcorp get hpa

# Manual scaling
kubectl -n ragcorp scale deployment ragcorp-backend --replicas=5
```

### Scale-down Protection

- Stabilization window: 5 minutes
- Maximum 10% scale-down per minute
- Pod Disruption Budget: minimum 1 pod

## Monitoring

Prometheus annotations are pre-configured:

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

## Troubleshooting

```bash
# Pod logs
kubectl -n ragcorp logs -l app.kubernetes.io/component=backend -f

# Describe pod
kubectl -n ragcorp describe pod -l app.kubernetes.io/component=backend

# Events
kubectl -n ragcorp get events --sort-by='.lastTimestamp'

# Port forward for local testing
kubectl -n ragcorp port-forward svc/ragcorp-backend 8000:8000
```

## Production Checklist

- [ ] Update secrets in `secret.yaml` or configure External Secrets
- [ ] Configure domain names in `ingress.yaml`
- [ ] Set up cert-manager for TLS
- [ ] Configure external PostgreSQL connection
- [ ] Review resource limits based on load testing
- [ ] Enable PodSecurityPolicy or Pod Security Standards
- [ ] Configure backup strategy for Redis (if using persistence)
