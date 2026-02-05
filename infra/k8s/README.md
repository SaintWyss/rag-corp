<!--
===============================================================================
TARJETA CRC - infra/k8s/README.md
===============================================================================
Responsabilidades:
- Describir la estructura K8s (base + overlays) sin drift.
- Indicar cómo aplicar base y overlays con comandos reales.

Colaboradores:
- infra/k8s/base/*
- infra/k8s/overlays/*
- infra/k8s/render_kustomize.sh

Invariantes:
- No incluir secretos reales.
- Mantener rutas coherentes con el repo.
===============================================================================
-->
# infra/k8s/ — README

> **Navegación:** [← Volver a infra/](../README.md) · [← Volver a raíz](../../README.md)

## TL;DR (30 segundos)

- **Qué es:** Manifiestos de Kubernetes para despliegue en producción.
- **Para qué sirve:** Definir cómo correr RAG Corp en un cluster de Kubernetes real.
- **Quién la usa:** DevOps/SRE al desplegar a staging/producción.
- **Impacto si se borra:** No hay forma declarativa de desplegar en k8s — tendrías que crear todo manualmente.

---

## Para alguien con 0 conocimientos

### ¿Qué problema resuelve?

Docker Compose es genial para desarrollo local, pero no para producción con alta disponibilidad. Kubernetes (k8s) es el estándar de la industria para correr aplicaciones en producción: escala automáticamente, se recupera de fallos, y maneja tráfico de forma inteligente.

Esta carpeta contiene todos los "manifiestos" — archivos YAML que le dicen a Kubernetes exactamente cómo desplegar cada componente de RAG Corp.

**Analogía:** Si Docker Compose es correr un restaurante familiar, Kubernetes es operar una cadena de restaurantes con gerentes, reglas de operación, y expansión automática según demanda.

### ¿Qué hay acá adentro?

```
k8s/
├── kustomization.yaml          # Wrapper (compatibilidad) -> base
├── base/                        # Manifiestos base (sin overlays)
│   ├── kustomization.yaml
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── backend-deployment.yaml
│   ├── backend-service.yaml
│   ├── backend-hpa.yaml
│   ├── frontend-deployment.yaml
│   ├── frontend-service.yaml
│   ├── redis-deployment.yaml
│   ├── ingress.yaml
│   ├── network-policy.yaml
│   └── pdb.yaml
├── overlays/
│   ├── staging/
│   └── prod/
└── render_kustomize.sh          # Render dockerizado (sin kubectl)
```

### ¿Cómo se usa paso a paso?

```bash
# 1. Aplicar base (compatibilidad)
kubectl apply -k infra/k8s/

# 2. Verificar que todo está corriendo
kubectl -n ragcorp get pods
kubectl -n ragcorp get svc

# 3. Ver logs del backend
kubectl -n ragcorp logs -l app.kubernetes.io/component=backend -f
```

---

## Para engineers / seniors

### Responsabilidades (SRP)

Esta carpeta DEBE contener:
- Manifiestos de Kubernetes para todos los componentes
- ConfigMaps y Secrets (con placeholders, no valores reales)
- Network policies y PDBs
- HPA y escalado

Esta carpeta NO DEBE contener:
- Valores reales de secrets (usar External Secrets Operator)
- Helm charts (esto es vanilla k8s/Kustomize)
- Configuración de CI/CD (eso va en `.github/workflows/`)
- Manifiestos para observabilidad en k8s (usar helm charts dedicados)

### Colaboradores y dependencias

| Componente | Dependencias |
|------------|--------------|
| `base/backend-deployment.yaml` | `base/secret.yaml`, `base/configmap.yaml`, imagen de container registry |
| `base/frontend-deployment.yaml` | `base/backend-service.yaml` (para conectar al API) |
| `base/ingress.yaml` | NGINX Ingress Controller, cert-manager |
| `base/backend-hpa.yaml` | Metrics Server instalado en cluster |

**Prerrequisitos del cluster:**
- Kubernetes 1.27+
- NGINX Ingress Controller
- cert-manager (para TLS)
- Metrics Server (para HPA)
- Container registry con las imágenes

### Contratos / Interfaces

| Manifest | Recursos que crea |
|----------|-------------------|
| `namespace.yaml` | Namespace `ragcorp` |
| `backend-deployment.yaml` | Deployment `ragcorp-backend` (2 replicas) |
| `backend-hpa.yaml` | HPA (2-10 pods, target CPU 70%) |
| `ingress.yaml` | Ingress con TLS |
| `network-policy.yaml` | Deny-all + allow específicos |

### Flujo de trabajo típico

**"Desplegar una nueva versión":**
1. Build y push de imagen al registry
2. Actualizar tag en `*-deployment.yaml`
3. `kubectl apply -k infra/k8s/`
4. Verificar rollout: `kubectl -n ragcorp rollout status deployment/ragcorp-backend`

**"Escalar manualmente":**
```bash
kubectl -n ragcorp scale deployment ragcorp-backend --replicas=5
```

**"Debug de un pod que no arranca":**
```bash
kubectl -n ragcorp describe pod <nombre-del-pod>
kubectl -n ragcorp logs <nombre-del-pod> --previous
```

**"Ver eventos del namespace":**
```bash
kubectl -n ragcorp get events --sort-by='.lastTimestamp'
```

### Riesgos y pitfalls

| Riesgo | Causa | Detección | Solución |
|--------|-------|-----------|----------|
| Secrets en texto plano | Olvidar usar External Secrets | `git log` muestra secrets | Rotar secrets, usar ESO |
| ImagePullBackOff | Registry privado sin credentials | `describe pod` | Crear imagePullSecret |
| CrashLoopBackOff | Error de app o config faltante | Logs del pod | Revisar logs y ConfigMap |
| HPA no escala | Metrics Server no instalado | `kubectl top pods` falla | Instalar Metrics Server |
| TLS no funciona | cert-manager mal configurado | Certificate no Ready | Verificar ClusterIssuer |

### Seguridad / Compliance

**Implementado:**
- ✅ Non-root containers (`runAsNonRoot: true`)
- ✅ Read-only filesystem (`readOnlyRootFilesystem: true`)
- ✅ Network policies (zero-trust)
- ✅ Pod Disruption Budgets
- ✅ Security contexts (dropped capabilities)
- ✅ TLS via cert-manager

**Secrets (en `secret.yaml`):**
- `DATABASE_URL` — conexión a PostgreSQL
- `GOOGLE_API_KEY` — API key de Google AI
- `REDIS_URL` — conexión a Redis

⚠️ **NUNCA commitear valores reales.** Usar External Secrets Operator o similar.

### Observabilidad / Operación

**Prometheus scraping habilitado en pods:**
```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

**Healthchecks:**
- Liveness: `/healthz`
- Readiness: `/readyz`

**Port-forward para debug local:**
```bash
kubectl -n ragcorp port-forward svc/ragcorp-backend 8000:8000
kubectl -n ragcorp port-forward svc/ragcorp-frontend 3000:3000
```

---

## CRC (Component/Folder CRC Card)

**Name:** `infra/k8s/`

**Responsibilities:**
1. Definir despliegue de backend en Kubernetes
2. Definir despliegue de frontend en Kubernetes
3. Configurar networking (ingress, services, policies)
4. Configurar auto-escalado (HPA)
5. Configurar seguridad (contexts, PDBs)

**Collaborators:**
- Container registry (provee imágenes)
- NGINX Ingress Controller (maneja tráfico)
- cert-manager (TLS certificates)
- External Secrets Operator (secrets management)
- Prometheus (scraping de métricas)

**Constraints:**
- Requiere Kubernetes 1.27+
- Requiere NGINX Ingress Controller
- Secrets son placeholders — necesitan External Secrets en prod
- HPA requiere Metrics Server

---

## Evidencia

- `infra/k8s/kustomization.yaml` — lista de recursos
- `infra/k8s/backend-deployment.yaml:45-60` — security context
- `infra/k8s/network-policy.yaml` — zero-trust policies
- `infra/k8s/backend-hpa.yaml:12-20` — scaling config

---

## FAQ rápido

**¿Puedo usar esto con Helm?**
Actualmente usa Kustomize vanilla. Se puede migrar a Helm si necesitás más flexibilidad.

**¿Por qué hay 2 replicas mínimo?**
Para alta disponibilidad. Si un pod muere, el otro sigue sirviendo.

**¿Dónde pongo las variables de entorno?**
En `configmap.yaml` (no-secretas) o `secret.yaml` (secretas).

**¿Cómo conecto a una DB externa?**
Actualizar `DATABASE_URL` en `secret.yaml` con la URL de conexión.

---

## Glosario

| Término | Definición |
|---------|------------|
| **Kubernetes (k8s)** | Orquestador de contenedores |
| **Manifest** | Archivo YAML que describe un recurso de k8s |
| **Deployment** | Recurso que define cómo correr pods |
| **Service** | Recurso que expone pods dentro del cluster |
| **Ingress** | Recurso que expone servicios al exterior |
| **HPA** | Horizontal Pod Autoscaler — escala automáticamente |
| **PDB** | Pod Disruption Budget — protege durante mantenimiento |
| **Kustomize** | Herramienta para customizar manifiestos |
| **Network Policy** | Firewall entre pods |

---

## Production Checklist

- [ ] Update `secret.yaml` with real credentials (or use External Secrets)
- [ ] Configure External Secrets Operator
- [ ] Update `ingress.yaml` with your domain
- [ ] Configure cert-manager ClusterIssuer
- [ ] Set up monitoring (Prometheus + Grafana in-cluster)
- [ ] Configure backup for Redis (if using persistence)
- [ ] Review resource limits based on load testing
- [ ] Enable Pod Security Standards
