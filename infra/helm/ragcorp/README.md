# ragcorp Helm Chart — Enterprise-ready

Este chart empaqueta RAG Corp para despliegues K8s-first: backend, worker, frontend, ingress opcional, config, autoscaling y toggles de observabilidad.

## Decisiones de diseño (explícitas)

1) **Imágenes por componente (single artifact):**
- Backend y worker usan la misma imagen base (`ragcorp/backend`).
- Frontend usa su propia imagen (`ragcorp/frontend`).

2) **Configuración por `values.yaml`:**
- Toda configuración no sensible vive en `values.yaml` → `ConfigMap`.
- Secretos se referencian via `existingSecret` o `ExternalSecrets` (no se almacenan en git).

3) **Métricas con auth:**
- `METRICS_REQUIRE_AUTH=true` por defecto (alineado con la política de producción).
- `/metrics` requiere API key/RBAC según configuración del backend.

4) **Ingress y SSE/timeouts:**
- Incluye annotations recomendadas (proxy-read/send/connect timeouts).
- Ajustar valores según tráfico SSE (streaming) y límites de carga.

## Instalación

```bash
# Instalar en un namespace existente
helm install ragcorp infra/helm/ragcorp -n <namespace> -f infra/helm/ragcorp/values.yaml

# Instalar creando namespace
helm install ragcorp infra/helm/ragcorp -n <namespace> --create-namespace -f infra/helm/ragcorp/values.yaml
```

## Upgrade / Rollback

```bash
helm upgrade ragcorp infra/helm/ragcorp -n <namespace> -f infra/helm/ragcorp/values.yaml
helm rollback ragcorp <REVISION> -n <namespace>
```

## Migrations

Por seguridad, **las migraciones están deshabilitadas por defecto**.

Opciones:
- **Paso externo (recomendado):** ejecutar migraciones con un job manual (controlado por ventana de mantenimiento).
- **Hook opcional:** habilitar `migrations.enabled=true` y `migrations.hook=true`.

## Secretos

No se versionan secretos. Usar uno de:
- `secrets.existingSecret: ragcorp-secrets`
- ExternalSecrets (recomendado en enterprise)

El Secret debe contener al menos:
- `DATABASE_URL`
- `GOOGLE_API_KEY`
- `JWT_SECRET`
- `API_KEYS_CONFIG` o `RBAC_CONFIG`

## Ingress

Para habilitar ingress:

```yaml
ingress:
  enabled: true
  className: nginx
  hosts:
    - host: ragcorp.example.com
      paths:
        - path: /
          pathType: Prefix
          service: frontend
    - host: api.ragcorp.example.com
      paths:
        - path: /
          pathType: Prefix
          service: backend
```

## Observabilidad

Si `observability.prometheus.enabled=true`, se agregan annotations de scraping en backend/worker.

## Validación local

```bash
helm lint infra/helm/ragcorp
helm template ragcorp infra/helm/ragcorp -f infra/helm/ragcorp/values.yaml > /tmp/ragcorp.yaml
```

## Estructura del chart

```
infra/helm/ragcorp/
├── Chart.yaml
├── values.yaml
├── values.schema.json
├── templates/
│   ├── backend-deployment.yaml
│   ├── backend-service.yaml
│   ├── backend-hpa.yaml
│   ├── worker-deployment.yaml
│   ├── frontend-deployment.yaml
│   ├── frontend-service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── serviceaccount.yaml
│   ├── rbac.yaml
│   ├── networkpolicy.yaml
│   ├── pdb.yaml
│   ├── migrations-job.yaml
│   ├── redis.yaml
│   ├── namespace.yaml
│   └── NOTES.txt
└── examples/
    ├── values-staging.yaml
    └── values-prod.yaml
```
