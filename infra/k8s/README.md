# RAG Corp Kubernetes Manifests

Production-ready Kubernetes deployment for RAG Corp.

## Prerequisites

- Kubernetes 1.27+
- kubectl configured
- NGINX Ingress Controller
- cert-manager (for TLS)
- Container registry access

## Quick Start

```bash
# 1. Create namespace and apply all resources
kubectl apply -k infra/k8s/

# 2. Check deployment status
kubectl -n ragcorp get pods
kubectl -n ragcorp get svc

# 3. View logs
kubectl -n ragcorp logs -l app.kubernetes.io/component=backend -f
```

## Configuration

### Secrets Setup

Before deploying, update `secret.yaml` with your actual values:

```bash
# Generate base64 encoded secrets
echo -n "postgresql://user:pass@host:5432/db" | base64
echo -n "your-google-api-key" | base64

# Apply secrets
kubectl apply -f infra/k8s/secret.yaml
```

### Using External Secrets Operator (Recommended)

For production, use External Secrets Operator with AWS Secrets Manager or HashiCorp Vault:

```yaml
# See commented example in secret.yaml
```

## Components

| Manifest | Description |
|----------|-------------|
| `namespace.yaml` | Dedicated namespace |
| `configmap.yaml` | Non-sensitive configuration |
| `secret.yaml` | Sensitive configuration (DB URL, API keys) |
| `backend-deployment.yaml` | FastAPI backend (2 replicas) |
| `backend-service.yaml` | Backend ClusterIP service |
| `backend-hpa.yaml` | Horizontal Pod Autoscaler (2-10 pods) |
| `frontend-deployment.yaml` | Next.js frontend (2 replicas) |
| `frontend-service.yaml` | Frontend ClusterIP service |
| `ingress.yaml` | NGINX Ingress with TLS |
| `redis-deployment.yaml` | Redis cache (optional) |
| `pdb.yaml` | Pod Disruption Budgets |
| `network-policy.yaml` | Zero-trust network policies |

## Security Features

- **Non-root containers**: All pods run as non-root user
- **Read-only filesystem**: Backend uses read-only root filesystem
- **Network policies**: Zero-trust networking (deny-all default)
- **Pod Disruption Budgets**: High availability during maintenance
- **Security contexts**: Dropped capabilities, no privilege escalation
- **TLS**: cert-manager with Let's Encrypt

## Scaling

HPA automatically scales backend pods based on:
- CPU utilization (target: 70%)
- Memory utilization (target: 80%)

Manual scaling:
```bash
kubectl -n ragcorp scale deployment ragcorp-backend --replicas=5
```

## Monitoring

Prometheus scraping is enabled via pod annotations:

```yaml
prometheus.io/scrape: "true"
prometheus.io/port: "8000"
prometheus.io/path: "/metrics"
```

## Troubleshooting

```bash
# Check pod status
kubectl -n ragcorp describe pod -l app.kubernetes.io/component=backend

# Check events
kubectl -n ragcorp get events --sort-by='.lastTimestamp'

# Port-forward for local testing
kubectl -n ragcorp port-forward svc/ragcorp-backend 8000:8000
kubectl -n ragcorp port-forward svc/ragcorp-frontend 3000:3000
```

## Production Checklist

- [ ] Update `secret.yaml` with real credentials
- [ ] Configure External Secrets Operator
- [ ] Update `ingress.yaml` with your domain
- [ ] Configure cert-manager cluster issuer
- [ ] Set up monitoring (Prometheus + Grafana)
- [ ] Configure backup for Redis (if using persistence)
- [ ] Review resource limits based on load testing
- [ ] Enable PodSecurityPolicy or Pod Security Standards
