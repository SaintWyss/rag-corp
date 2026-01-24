# infra/grafana/dashboards/ — README

> **Navegación:** [← Volver a grafana/](../README.md) · [← Volver a infra/](../../README.md)

## TL;DR (30 segundos)

- **Qué es:** Archivos JSON que definen dashboards de Grafana.
- **Para qué sirve:** Visualizar métricas del sistema con gráficos pre-diseñados.
- **Quién la usa:** Grafana los carga automáticamente al iniciar.
- **Impacto si se borra:** Grafana arranca sin dashboards — hay que crearlos manualmente.

---

## Para alguien con 0 conocimientos

### ¿Qué problema resuelve?

Un dashboard de Grafana tiene muchos paneles (gráficos), cada uno con su query, colores, umbrales, etc. Configurar eso manualmente cada vez que recreás el contenedor sería tedioso.

Estos archivos JSON guardan toda esa configuración para que aparezca automáticamente.

### ¿Qué hay acá adentro?

```
dashboards/
├── ragcorp-api-performance.json   # 20KB - Latencia, throughput, errores
├── ragcorp-operations.json        # 18KB - Métricas operacionales
├── ragcorp-overview.json          # 3KB  - Vista general
└── ragcorp-postgres.json          # 17KB - Métricas de PostgreSQL
```

| Dashboard | Qué muestra |
|-----------|-------------|
| **Overview** | Estado general del sistema en un vistazo |
| **API Performance** | Latencia p50/p95/p99, requests/s, tasa de errores |
| **Operations** | Métricas de negocio: documentos procesados, queries |
| **PostgreSQL** | Conexiones, cache hit rate, transacciones |

### ¿Cómo se usa paso a paso?

**Ver los dashboards:**
1. `docker compose --profile observability up -d`
2. Abrir http://localhost:3001
3. Login: admin / admin
4. Menú izquierdo → Dashboards → Folder "RAG Corp"

---

## Para engineers / seniors

### Responsabilidades (SRP)

Esta carpeta DEBE contener:
- Dashboards JSON exportados de Grafana
- Solo dashboards relacionados con RAG Corp

Esta carpeta NO DEBE contener:
- Dashboards de terceros no customizados
- Configuración de Grafana (va en `provisioning-*.yml`)
- Alertas (van en `prometheus/alerts.yml`)

### Estructura de un dashboard JSON

```json
{
  "title": "RAG Corp - API Performance",
  "uid": "ragcorp-api",           // Identificador único
  "panels": [...],                 // Lista de paneles
  "templating": {...},             // Variables del dashboard
  "time": {...},                   // Rango de tiempo default
  "refresh": "30s"                 // Auto-refresh
}
```

### Flujo de trabajo típico

**"Crear un nuevo dashboard":**
1. En Grafana UI: New → Dashboard
2. Agregar paneles con queries PromQL
3. Click en ⚙️ → JSON Model → Copiar
4. Guardar como `infra/grafana/dashboards/nombre.json`
5. Commit

**"Modificar un dashboard existente":**
1. Editar en Grafana UI
2. Exportar JSON Model
3. Reemplazar archivo en esta carpeta
4. Commit

**Tips para queries PromQL comunes:**

```promql
# Requests por segundo
rate(rag_requests_total[5m])

# Latencia p95
histogram_quantile(0.95, rate(rag_request_latency_seconds_bucket[5m]))

# Tasa de errores
sum(rate(rag_requests_total{status=~"5.."}[5m])) / sum(rate(rag_requests_total[5m]))
```

### Riesgos y pitfalls

| Riesgo | Detección | Solución |
|--------|-----------|----------|
| JSON syntax error | Grafana no carga dashboard | Validar con `jq . archivo.json` |
| UID duplicada | Dashboard sobrescribe otro | Usar UIDs únicas descriptivas |
| Métricas inexistentes | Panel muestra "No data" | Verificar que backend expone la métrica |
| Ediciones perdidas | Dashboard vuelve a versión archivo | Siempre exportar y guardar en repo |

---

## CRC (Component/Folder CRC Card)

**Name:** `infra/grafana/dashboards/`

**Responsibilities:**
1. Almacenar dashboards JSON de Grafana
2. Proveer visualizaciones del sistema

**Collaborators:**
- `provisioning-dashboards.yml` (configura que se carguen)
- Prometheus (servido como datasource)
- Backend/Worker (exponen las métricas)

**Constraints:**
- UIDs deben ser únicas
- Queries deben usar métricas que el backend expone
- Compatible con Grafana 10.x

---

## Evidencia

- `infra/grafana/provisioning-dashboards.yml:10-11` — referencia al path de dashboards
- Archivos `.json` en esta carpeta

---

## FAQ rápido

**¿Cómo exporto un dashboard?**
En Grafana: Dashboard → Settings (⚙️) → JSON Model → Copiar

**¿Por qué mis paneles no muestran datos?**
1. Verificar que Prometheus está corriendo
2. Verificar que el backend expone `/metrics`
3. Probar la query en Prometheus UI

**¿Puedo editar directamente el JSON?**
Sí, pero es más fácil editar en UI y exportar.
