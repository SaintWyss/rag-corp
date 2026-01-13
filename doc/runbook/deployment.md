# Deployment Guide

**Project:** RAG Corp  
**Last Updated:** 2026-01-13

---

## Overview

RAG Corp supports multiple deployment strategies:

| Environment | Method | Config |
|-------------|--------|--------|
| Development | Docker Compose | `compose.yaml` |
| Staging | Docker Compose | `compose.prod.yaml` |
| Production | Kubernetes | `infra/k8s/` |

---

## Prerequisites

### Required Secrets

| Secret | Description | Where |
|--------|-------------|-------|
| `GOOGLE_API_KEY` | Gemini API key | Google Cloud Console |
| `DATABASE_URL` | PostgreSQL connection | Managed DB or self-hosted |
| `API_KEYS` | Application API keys | Generate secure random keys |

### Infrastructure Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 1 core | 2 cores |
| Memory | 1 GB | 2 GB |
| Storage | 10 GB | 50 GB (depends on documents) |
| PostgreSQL | 14+ with pgvector | 16 with pgvector 0.8+ |

---

## Docker Compose Deployment

### Staging/Production with compose.prod.yaml

```bash
# 1. Configure environment
cp .env.example .env.prod
# Edit .env.prod with production values

# 2. Build production images
docker compose -f compose.prod.yaml build

# 3. Start services
docker compose -f compose.prod.yaml up -d

# 4. Run migrations
docker compose -f compose.prod.yaml exec backend alembic upgrade head

# 5. Verify health
curl http://localhost:8000/healthz?full=true
```

### Environment Variables (Production)

```bash
# Required
DATABASE_URL=postgresql://user:pass@db-host:5432/ragcorp
GOOGLE_API_KEY=your-production-key
API_KEYS=prod-key-1:ingest,ask;metrics-key:metrics

# Security
ALLOWED_ORIGINS=https://app.yourdomain.com
RATE_LIMIT_RPS=50

# Performance
DB_POOL_MIN_SIZE=5
DB_POOL_MAX_SIZE=20

# Observability
LOG_LEVEL=INFO
OTEL_ENABLED=1
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
```

---

## Database Migrations

### Running Migrations

```bash
# Check current version
docker compose exec backend alembic current

# Apply all pending migrations
docker compose exec backend alembic upgrade head

# Apply specific migration
docker compose exec backend alembic upgrade <revision>
```

### Creating New Migrations

```bash
# Auto-generate from model changes
cd backend
alembic revision --autogenerate -m "add_new_column"

# Manual migration
alembic revision -m "custom_migration"
```

### Migration Best Practices

1. **Always test migrations** in staging first
2. **Backup database** before production migrations
3. **Use transactions** (Alembic does this by default)
4. **Write downgrade()** for every upgrade()

```python
# Example migration
def upgrade():
    op.add_column('documents', sa.Column('category', sa.String(100)))

def downgrade():
    op.drop_column('documents', 'category')
```

---

## Blue-Green Deployment

### Strategy

1. **Blue** = Current production
2. **Green** = New version

```
                    ┌─────────────┐
                    │   Load      │
                    │  Balancer   │
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                         │
        ┌─────▼─────┐            ┌─────▼─────┐
        │   Blue    │            │   Green   │
        │  (v1.0)   │            │  (v1.1)   │
        │  ACTIVE   │            │  STANDBY  │
        └───────────┘            └───────────┘
```

### Procedure

```bash
# 1. Deploy green environment
docker compose -f compose.green.yaml up -d

# 2. Run migrations on green (if needed)
docker compose -f compose.green.yaml exec backend alembic upgrade head

# 3. Health check green
curl http://green-host:8000/healthz?full=true

# 4. Run smoke tests
pnpm e2e --env BASE_URL=http://green-host:8000

# 5. Switch traffic (at load balancer level)
# ... configure your LB to route to green

# 6. Monitor for errors
# If issues: revert LB to blue

# 7. After validation, tear down blue
docker compose -f compose.blue.yaml down
```

### Rollback

```bash
# Immediate: Switch LB back to blue
# LB config: route traffic to blue-host:8000

# If blue is down, redeploy previous version
docker compose -f compose.prod.yaml down
git checkout v1.0.0
docker compose -f compose.prod.yaml up -d
```

---

## Kubernetes Deployment

### Prerequisites

- Kubernetes 1.28+
- kubectl configured
- Helm 3.x (optional)

### Deploy with kubectl

```bash
# 1. Create namespace
kubectl create namespace ragcorp

# 2. Create secrets
kubectl create secret generic ragcorp-secrets \
  --from-literal=google-api-key=$GOOGLE_API_KEY \
  --from-literal=database-url=$DATABASE_URL \
  --from-literal=api-keys=$API_KEYS \
  -n ragcorp

# 3. Apply manifests
kubectl apply -f infra/k8s/ -n ragcorp

# 4. Check deployment
kubectl get pods -n ragcorp
kubectl logs -f deployment/ragcorp-backend -n ragcorp
```

### Scaling

```bash
# Scale backend
kubectl scale deployment ragcorp-backend --replicas=3 -n ragcorp

# Autoscaling
kubectl apply -f - <<EOF
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ragcorp-backend-hpa
  namespace: ragcorp
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ragcorp-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
EOF
```

---

## Rollback Procedures

### Docker Compose Rollback

```bash
# 1. Check current version
docker compose exec backend cat /app/VERSION || echo "No version file"

# 2. Stop current deployment
docker compose -f compose.prod.yaml down

# 3. Checkout previous version
git checkout v1.0.0  # or specific commit

# 4. Rebuild and deploy
docker compose -f compose.prod.yaml build
docker compose -f compose.prod.yaml up -d

# 5. Rollback migrations (if needed)
docker compose exec backend alembic downgrade -1
```

### Kubernetes Rollback

```bash
# View rollout history
kubectl rollout history deployment/ragcorp-backend -n ragcorp

# Rollback to previous version
kubectl rollout undo deployment/ragcorp-backend -n ragcorp

# Rollback to specific revision
kubectl rollout undo deployment/ragcorp-backend --to-revision=2 -n ragcorp

# Check rollback status
kubectl rollout status deployment/ragcorp-backend -n ragcorp
```

### Database Rollback

```bash
# CAUTION: Data loss possible!

# 1. Check current migration
docker compose exec backend alembic current

# 2. Downgrade one migration
docker compose exec backend alembic downgrade -1

# 3. Or downgrade to specific revision
docker compose exec backend alembic downgrade abc123

# 4. Verify
docker compose exec backend alembic current
```

---

## Health Checks

### Endpoints

| Endpoint | Purpose | Frequency |
|----------|---------|-----------|
| `/healthz` | Liveness (DB check) | Every 10s |
| `/healthz?full=true` | Readiness (DB + Google) | Every 30s |
| `/metrics` | Prometheus metrics | Every 15s |

### Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /healthz?full=true
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 30
```

---

## Monitoring

### Grafana Dashboards

Access: http://localhost:3001 (staging) or your Grafana URL (production)

| Dashboard | Purpose |
|-----------|---------|
| RAG Corp - API Performance | Request rates, latency, errors |
| RAG Corp - PostgreSQL | DB connections, queries, storage |
| RAG Corp - Operations | SLOs, alerts, infrastructure |

### Alerts

Alerts are configured in `infra/prometheus/alerts.yml`:

| Alert | Threshold | Severity |
|-------|-----------|----------|
| High Error Rate | >5% for 5m | critical |
| High Latency | p95 >2s for 5m | warning |
| DB Connection Failures | >0 for 2m | critical |
| High Memory Usage | >90% for 5m | warning |

---

## Checklist

### Pre-Deployment

- [ ] All tests passing in CI
- [ ] Database backup taken
- [ ] Rollback plan documented
- [ ] Team notified

### Deployment

- [ ] New version deployed
- [ ] Migrations applied
- [ ] Health checks passing
- [ ] Smoke tests passing

### Post-Deployment

- [ ] Monitoring dashboards checked
- [ ] Error rates normal
- [ ] Performance acceptable
- [ ] Stakeholders notified

---

## Troubleshooting

For common deployment issues, see [troubleshooting.md](troubleshooting.md).
