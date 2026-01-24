# infra/ — README

> **Navegación:** [← Volver a raíz del repo](../README.md)

## TL;DR (30 segundos)

- **Qué es:** Infraestructura como Código (IaC) para desplegar y monitorear RAG Corp.
- **Para qué sirve:** Configuraciones de base de datos, observabilidad (métricas/alertas/dashboards), y manifiestos de Kubernetes para producción.
- **Quién la usa:** DevOps, SREs, y developers cuando despliegan o debuggean.
- **Impacto si se borra:** Sin init.sql no hay pgvector; sin prometheus/grafana no hay monitoreo; sin k8s/ no hay producción.

---

## Para alguien con 0 conocimientos

### ¿Qué problema resuelve?

Cuando tu aplicación pasa de "funciona en mi máquina" a "funciona en producción para miles de usuarios", necesitás muchas cosas extra: una base de datos bien configurada, gráficos para ver si algo anda lento, alertas que te avisen si algo se rompe, y archivos que le digan a Kubernetes cómo correr tu app.

**Analogía:** Si tu app es un auto, `infra/` es el taller mecánico: las herramientas de diagnóstico (Prometheus/Grafana), las instrucciones del motor (Postgres init), y el manual de ensamblaje (Kubernetes manifests).

### ¿Qué hay acá adentro?

```
infra/
├── grafana/          # Dashboards visuales para métricas
│   └── dashboards/   # JSONs de cada dashboard
├── k8s/              # Manifiestos de Kubernetes (producción)
├── postgres/         # Script de inicialización de PostgreSQL
└── prometheus/       # Configuración de métricas y alertas
```

| Carpeta | Propósito | Archivo clave |
|---------|-----------|---------------|
| `grafana/` | Paneles visuales para ver métricas | `provisioning-*.yml` |
| `k8s/` | Despliegue en Kubernetes | `kustomization.yaml` |
| `postgres/` | Habilitar extensión pgvector | `init.sql` |
| `prometheus/` | Recolectar métricas + reglas de alerta | `prometheus.yml`, `alerts.yml` |

### ¿Cómo se usa paso a paso?

**Levantar observabilidad local (Docker):**
```bash
docker compose --profile observability up -d
# Acceder a Grafana: http://localhost:3001 (admin/admin)
# Acceder a Prometheus: http://localhost:9090
```

**Desplegar en Kubernetes:**
```bash
kubectl apply -k infra/k8s/
```

---

## Para engineers / seniors

### Responsabilidades (SRP)

Esta carpeta DEBE contener:
- Configuración de infraestructura de soporte (no lógica de negocio)
- Scripts de inicialización de servicios externos (DB, cache)
- Definiciones de observabilidad (métricas, alertas, dashboards)
- Manifiestos de despliegue (Kubernetes, etc.)

Esta carpeta NO DEBE contener:
- Código de aplicación (eso va en `apps/`)
- Tests (eso va en `tests/`)
- Documentación de usuario (eso va en `docs/`)
- Secrets reales (solo placeholders/templates)
- Configuración de CI/CD (eso va en `.github/workflows/`)

### Colaboradores y dependencias

| Consumidor | Cómo lo usa |
|------------|-------------|
| `compose.yaml` | Monta `infra/prometheus/`, `infra/grafana/`, `infra/postgres/init.sql` |
| `.github/workflows/ci.yml` | NO usa infra directamente (CI corre sin observability) |
| Kubernetes cluster | Consume `infra/k8s/` via `kubectl apply -k` |

**Dependencias externas:**
- `pgvector/pgvector` image (para `init.sql`)
- `prom/prometheus` image
- `grafana/grafana` image

### Contratos / Interfaces relevantes

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `compose.yaml:156-175` | Compose volumes | Monta configs de Prometheus/Grafana |
| `compose.yaml:12` | Compose volumes | Monta `init.sql` en postgres |
| `prometheus.yml:22-32` | Scrape config | Define targets de métricas |

### Flujo de trabajo típico

**"Quiero agregar una métrica nueva":**
1. Exponer métrica en backend (`/metrics`)
2. Verificar que `prometheus.yml` scrapea el target
3. Crear panel en Grafana (nuevo JSON en `dashboards/`)
4. (Opcional) Agregar alerta en `alerts.yml`

**"Una alerta está disparándose mal":**
1. Ir a Prometheus UI → Alerts
2. Ver la expresión PromQL en `alerts.yml`
3. Ejecutar manualmente en Prometheus para debuggear
4. Ajustar threshold o ventana de tiempo

### Riesgos y pitfalls

| Riesgo | Detección | Mitigación |
|--------|-----------|------------|
| `init.sql` no corre | Error "extension vector does not exist" | Verificar mount en compose, borrar volume y recrear |
| Prometheus no scrapea | Target "down" en Prometheus UI | Verificar hostname (debe ser nombre del service en compose) |
| Dashboard no aparece | Folder vacío en Grafana | Verificar provisioning-dashboards.yml path |
| Alertas no disparan | Alertmanager no configurado | Es intencional en dev; configurar para prod |

### Seguridad / Compliance

- **Secrets:** `k8s/secret.yaml` contiene PLACEHOLDERS, nunca valores reales
- **Grafana password:** Default `admin/admin` en dev, cambiar para prod via `GRAFANA_PASSWORD`
- **Network:** En k8s, `network-policy.yaml` implementa zero-trust

### Observabilidad / Operación

| Servicio | Puerto | Healthcheck |
|----------|--------|-------------|
| Prometheus | 9090 | `/-/healthy` |
| Grafana | 3001 (local) / 3000 (container) | `/api/health` |
| postgres-exporter | 9187 | N/A |

---

## CRC (Component/Folder CRC Card)

**Name:** `infra/`

**Responsibilities:**
1. Proveer extensión pgvector para PostgreSQL
2. Definir scrape targets para Prometheus
3. Definir reglas de alerting
4. Proveer dashboards pre-configurados para Grafana
5. Definir manifiestos de Kubernetes para producción

**Collaborators:**
- `compose.yaml` (monta archivos)
- `apps/backend` (expone `/metrics`)
- Kubernetes cluster (consume manifests)
- Alertmanager (recibe alertas - no desplegado por defecto)

**Constraints:**
- Los dashboards JSON deben ser compatibles con Grafana 10.x
- `init.sql` debe ser idempotente (`IF NOT EXISTS`)
- Los k8s manifests asumen NGINX Ingress Controller

---

## Evidencia

- `compose.yaml:12` — mount de `init.sql`
- `compose.yaml:156-175` — servicios prometheus y grafana
- `infra/prometheus/prometheus.yml:22-32` — scrape config
- `infra/k8s/kustomization.yaml` — orquestación de manifests

---

## FAQ rápido

**¿Puedo borrar `infra/`?**
- Solo si no usás observabilidad local ni despliegue en k8s. El `init.sql` es crítico para pgvector.

**¿Dónde agrego un nuevo dashboard?**
- En `infra/grafana/dashboards/` como archivo JSON.

**¿A quién afecta si cambio `alerts.yml`?**
- A quien reciba alertas (Slack, PagerDuty, etc.) — requiere Alertmanager configurado.

---

## Glosario

| Término | Definición |
|---------|------------|
| **IaC** | Infrastructure as Code — definir infra en archivos versionables |
| **Prometheus** | Sistema de monitoreo que recolecta métricas de tus apps |
| **Grafana** | UI para visualizar métricas con gráficos |
| **pgvector** | Extensión de PostgreSQL para búsqueda vectorial (IA/embeddings) |
| **Kubernetes (k8s)** | Orquestador de contenedores para producción |
| **Scrape** | Acción de Prometheus de "ir a buscar" métricas a un endpoint |
| **PromQL** | Lenguaje de queries de Prometheus |

---

## Índice de subcarpetas

- [grafana/](./grafana/README.md) — Configuración y dashboards de Grafana
- [k8s/](./k8s/README.md) — Manifiestos de Kubernetes
- [postgres/](./postgres/README.md) — Script de inicialización de PostgreSQL
- [prometheus/](./prometheus/README.md) — Configuración de Prometheus y alertas
