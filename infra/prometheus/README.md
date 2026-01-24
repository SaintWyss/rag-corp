# infra/prometheus/ — README

> **Navegación:** [← Volver a infra/](../README.md) · [← Volver a raíz](../../README.md)

## TL;DR (30 segundos)

- **Qué es:** Configuración de Prometheus (sistema de monitoreo).
- **Para qué sirve:** Recolectar métricas del backend/worker/DB y definir alertas automáticas.
- **Quién la usa:** Docker Compose (profile `observability`) y operaciones/SRE.
- **Impacto si se borra:** Sin métricas ni alertas — el sistema corre pero "a ciegas".

---

## Para alguien con 0 conocimientos

### ¿Qué problema resuelve?

Cuando tu aplicación está corriendo, ¿cómo sabés si anda bien? ¿Si está lenta? ¿Si hay muchos errores? Prometheus es como un médico que constantemente le toma el pulso a tu app y anota los resultados.

- `prometheus.yml` le dice a Prometheus **dónde buscar** esas métricas
- `alerts.yml` define **cuándo preocuparse** (ej: "si hay más de 5% de errores, avisame")

### ¿Qué hay acá adentro?

```
prometheus/
├── prometheus.yml   # Configuración principal: qué monitorear
└── alerts.yml       # Reglas de alertas: cuándo disparar
```

| Archivo | Propósito |
|---------|-----------|
| `prometheus.yml` | Define los "targets" (endpoints a scrapear) |
| `alerts.yml` | Define reglas de alerta con thresholds |

### ¿Cómo se usa paso a paso?

**Levantar Prometheus localmente:**
```bash
docker compose --profile observability up -d
# Acceder: http://localhost:9090
```

**Ver métricas del backend:**
1. Ir a http://localhost:9090
2. En el campo de query, escribir: `rag_requests_total`
3. Click en "Execute"

**Ver alertas activas:**
1. Ir a http://localhost:9090/alerts
2. Ver estado de cada regla (inactive/pending/firing)

---

## Para engineers / seniors

### Responsabilidades (SRP)

Esta carpeta DEBE contener:
- Configuración de scrape targets de Prometheus
- Reglas de alerting (PromQL)
- Configuración de Alertmanager (cuando se agregue)

Esta carpeta NO DEBE contener:
- Dashboards (eso va en `grafana/`)
- Código de instrumentación (eso va en `apps/backend`)
- Configuración de notificaciones (Slack/PagerDuty — va en Alertmanager config)

### Colaboradores y dependencias

| Consumidor | Cómo lo usa |
|------------|-------------|
| `compose.yaml:152-166` | Servicio `prometheus` monta estos archivos |
| `apps/backend` | Expone `/metrics` en formato Prometheus |
| `worker` | Expone `/metrics` en puerto 8001 |
| `postgres-exporter` | Expone métricas de PostgreSQL |
| Grafana | Usa Prometheus como datasource |

### Contratos / Interfaces

**Scrape targets definidos en `prometheus.yml`:**

| Job | Target | Puerto | Path |
|-----|--------|--------|------|
| `ragcorp-backend` | `backend:8000` | 8000 | `/metrics` |
| `ragcorp-worker` | `worker:8001` | 8001 | `/metrics` |
| `postgres` | `postgres-exporter:9187` | 9187 | `/metrics` |
| `prometheus` | `localhost:9090` | 9090 | `/metrics` |

**Grupos de alertas en `alerts.yml`:**

| Grupo | Descripción | Severidades |
|-------|-------------|-------------|
| `ragcorp-api` | Errores, latencia, disponibilidad | warning, critical |
| `ragcorp-database` | PostgreSQL health, connections, cache | warning, critical |
| `ragcorp-infrastructure` | CPU, memoria, disco | warning, critical |
| `ragcorp-slo` | SLOs de disponibilidad y latencia | warning, critical |

### Flujo de trabajo típico

**"Agregar una nueva alerta":**
1. Abrir `alerts.yml`
2. Agregar regla en el grupo apropiado:
   ```yaml
   - alert: NombreDeAlerta
     expr: |
       tu_metrica > threshold
     for: 5m
     labels:
       severity: warning
     annotations:
       summary: "Descripción corta"
       description: "Detalles con {{ $value }}"
   ```
3. Reiniciar Prometheus: `docker compose restart prometheus`
4. Verificar en http://localhost:9090/alerts

**"La alerta dispara incorrectamente":**
1. Ir a Prometheus UI → Graph
2. Ejecutar la expresión de la alerta manualmente
3. Ajustar threshold o ventana `for:`
4. Verificar que la métrica tiene datos (`up{job="nombre"} == 1`)

### Riesgos y pitfalls

| Riesgo | Causa | Detección | Solución |
|--------|-------|-----------|----------|
| Target "down" | Hostname incorrecto | UI → Status → Targets | Usar nombre del service en compose |
| Alertas nunca disparan | Alertmanager no configurado | Es intencional en dev | Para prod: configurar Alertmanager |
| Métricas vacías | Backend no expone `/metrics` | Query retorna "No data" | Verificar instrumentación en backend |
| Syntax error en alert | YAML inválido | Prometheus no arranca | Ver logs: `docker compose logs prometheus` |

### Seguridad / Compliance

- Prometheus NO tiene autenticación por defecto (solo acceso local)
- Las métricas no contienen PII (solo contadores/histogramas)
- Para producción: usar NetworkPolicy o proxy con auth

### Observabilidad meta

| Qué revisar | Dónde |
|-------------|-------|
| Estado de targets | http://localhost:9090/targets |
| Alertas activas | http://localhost:9090/alerts |
| Config cargada | http://localhost:9090/config |
| Health de Prometheus | http://localhost:9090/-/healthy |

---

## CRC (Component/Folder CRC Card)

**Name:** `infra/prometheus/`

**Responsibilities:**
1. Definir qué servicios monitorear (scrape config)
2. Definir reglas de alerting con thresholds
3. Cargar reglas desde `alerts.yml`
4. (Futuro) Configurar Alertmanager para notificaciones

**Collaborators:**
- Docker Compose (monta archivos, corre contenedor)
- Backend/Worker (exponen `/metrics`)
- postgres-exporter (expone métricas de DB)
- Grafana (consume datos de Prometheus)
- Alertmanager (recibe alertas — no desplegado por defecto)

**Constraints:**
- Los hostnames en `prometheus.yml` deben coincidir con service names de compose
- Las métricas deben existir antes de crear alertas
- Intervalo mínimo de scrape: 10s (para no sobrecargar)

---

## Evidencia

- `infra/prometheus/prometheus.yml:22-32` — scrape configs
- `infra/prometheus/alerts.yml:5-92` — reglas de alerta de API
- `compose.yaml:152-166` — servicio prometheus con mounts

---

## FAQ rápido

**¿Puedo borrar esto?**
Solo si no necesitás monitoreo. El sistema funciona, pero no tenés visibilidad.

**¿Por qué las alertas no mandan notificaciones?**
Porque Alertmanager no está configurado. Es intencional para desarrollo.

**¿Dónde veo los dashboards?**
En Grafana (http://localhost:3001), no en Prometheus.

---

## Glosario

| Término | Definición |
|---------|------------|
| **Prometheus** | Sistema de monitoreo que hace "pull" de métricas |
| **Scrape** | Acción de ir a buscar métricas a un endpoint |
| **Target** | Un endpoint del cual Prometheus recolecta métricas |
| **PromQL** | Lenguaje de queries de Prometheus |
| **Alert rule** | Condición que cuando se cumple, dispara una alerta |
| **Alertmanager** | Servicio que recibe alertas y las rutea (email, Slack, etc.) |
| **SLO** | Service Level Objective — objetivo de calidad de servicio |
