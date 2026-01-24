# infra/grafana/ — README

> **Navegación:** [← Volver a infra/](../README.md) · [← Volver a raíz](../../README.md)

## TL;DR (30 segundos)

- **Qué es:** Configuración de Grafana (paneles de visualización de métricas).
- **Para qué sirve:** Ver gráficos bonitos de tus métricas en lugar de números crudos.
- **Quién la usa:** DevOps, SREs, y cualquiera que quiera ver cómo anda el sistema.
- **Impacto si se borra:** Grafana arranca vacío — hay que configurar dashboards manualmente cada vez.

---

## Para alguien con 0 conocimientos

### ¿Qué problema resuelve?

Prometheus guarda métricas, pero verlas como números es difícil. Grafana transforma esos números en gráficos que cualquiera puede entender: líneas de latencia, barras de errores, gauges de uso de CPU.

Esta carpeta contiene los dashboards **pre-armados** para que Grafana los cargue automáticamente al iniciar.

**Analogía:** Prometheus es la planilla de Excel con datos; Grafana es el gráfico que armás arriba.

### ¿Qué hay acá adentro?

```
grafana/
├── provisioning-dashboards.yml   # Le dice a Grafana dónde buscar dashboards
├── provisioning-datasources.yml  # Le dice a Grafana que use Prometheus
└── dashboards/                   # Los dashboards en formato JSON
    ├── ragcorp-api-performance.json
    ├── ragcorp-operations.json
    ├── ragcorp-overview.json
    └── ragcorp-postgres.json
```

| Archivo | Propósito |
|---------|-----------|
| `provisioning-datasources.yml` | Conecta Grafana con Prometheus |
| `provisioning-dashboards.yml` | Configura auto-carga de dashboards |
| `dashboards/*.json` | Los paneles visuales en sí |

### ¿Cómo se usa paso a paso?

**Acceder a Grafana:**
```bash
docker compose --profile observability up -d
# Abrir: http://localhost:3001
# Usuario: admin
# Password: admin (o valor de GRAFANA_PASSWORD)
```

**Ver un dashboard:**
1. En el menú izquierdo, click en "Dashboards"
2. Expandir carpeta "RAG Corp"
3. Click en cualquier dashboard

---

## Para engineers / seniors

### Responsabilidades (SRP)

Esta carpeta DEBE contener:
- Archivos de provisioning para Grafana (datasources, dashboards)
- Dashboards JSON exportados

Esta carpeta NO DEBE contener:
- Configuración de usuarios/permisos (eso va en Grafana UI o helm values)
- Plugins custom de Grafana
- Alertas (eso está en `prometheus/alerts.yml`)

### Colaboradores y dependencias

| Consumidor | Cómo lo usa |
|------------|-------------|
| `compose.yaml:169-184` | Servicio `grafana` monta estos archivos |
| Prometheus | Grafana lo usa como datasource |
| Dashboards JSON | Son cargados por provisioning-dashboards.yml |

### Contratos / Interfaces

**Provisioning files:**

| Archivo | Se monta en | Propósito |
|---------|-------------|-----------|
| `provisioning-datasources.yml` | `/etc/grafana/provisioning/datasources/` | Define datasources |
| `provisioning-dashboards.yml` | `/etc/grafana/provisioning/dashboards/` | Define providers de dashboards |
| `dashboards/` | `/var/lib/grafana/dashboards/` | Contiene los JSONs |

**Dashboards disponibles:**

| Dashboard | Métricas que muestra |
|-----------|----------------------|
| `ragcorp-overview.json` | Vista general del sistema |
| `ragcorp-api-performance.json` | Latencia, throughput, errores del API |
| `ragcorp-operations.json` | Métricas operacionales |
| `ragcorp-postgres.json` | PostgreSQL: conexiones, cache, queries |

### Flujo de trabajo típico

**"Agregar un nuevo dashboard":**
1. Crear dashboard en Grafana UI
2. Click en ⚙️ (Settings) → JSON Model
3. Copiar el JSON
4. Guardar en `dashboards/nombre-descriptivo.json`
5. Commit al repo
6. Al reiniciar Grafana, el dashboard aparece

**"El dashboard no aparece":**
1. Verificar que el JSON está en `dashboards/`
2. Verificar que `provisioning-dashboards.yml` apunta al path correcto
3. Ver logs: `docker compose logs grafana`
4. Verificar permisos del archivo

**"Quiero editar un dashboard existente":**
1. Editar en UI de Grafana
2. Exportar JSON Model
3. Reemplazar el archivo en `dashboards/`
4. Commit

### Riesgos y pitfalls

| Riesgo | Causa | Detección | Solución |
|--------|-------|-----------|----------|
| Dashboard vacío | Prometheus sin datos | Paneles muestran "No data" | Verificar que prometheus está corriendo y scrapeando |
| Dashboard no carga | JSON inválido | Error en logs de Grafana | Validar JSON syntax |
| Ediciones se pierden | Grafana recarga de archivos | Dashboard vuelve a versión de archivo | Exportar y guardar en repo |
| Datasource falla | Prometheus URL incorrecta | Error de conexión en dashboard | Verificar `provisioning-datasources.yml` |

### Seguridad / Compliance

- **Credenciales:** Password default `admin/admin` — cambiar via `GRAFANA_PASSWORD`
- **Acceso:** Solo local en dev (puerto 3001)
- **Data:** Dashboards no contienen secrets

---

## CRC (Component/Folder CRC Card)

**Name:** `infra/grafana/`

**Responsibilities:**
1. Configurar datasource de Prometheus
2. Proveer dashboards pre-configurados
3. Habilitar auto-provisioning al iniciar Grafana

**Collaborators:**
- Docker Compose (monta archivos)
- Prometheus (sirve como datasource)
- Grafana container (consume provisioning)

**Constraints:**
- Dashboards deben ser compatibles con Grafana 10.x
- Las queries en dashboards asumen nombres de métricas del backend
- El path en `provisioning-dashboards.yml` debe coincidir con el mount

---

## Evidencia

- `infra/grafana/provisioning-datasources.yml:4-9` — datasource Prometheus
- `infra/grafana/provisioning-dashboards.yml:4-11` — provider de dashboards
- `compose.yaml:173-175` — mounts de grafana

---

## FAQ rápido

**¿Puedo borrar esto?**
Grafana funcionará, pero arrancará vacío cada vez.

**¿Dónde agrego un nuevo dashboard?**
En `dashboards/` como archivo `.json`.

**¿Por qué mis cambios en UI desaparecen?**
Grafana recarga de los archivos cada 30s. Exportá y guardá en el repo.

---

## Glosario

| Término | Definición |
|---------|------------|
| **Grafana** | Plataforma de visualización de métricas |
| **Dashboard** | Colección de paneles con gráficos |
| **Panel** | Un gráfico individual dentro de un dashboard |
| **Datasource** | Fuente de datos (en este caso, Prometheus) |
| **Provisioning** | Configuración automática al iniciar |
| **JSON Model** | Representación del dashboard en JSON |

---

## Subcarpetas

- [dashboards/](./dashboards/README.md) — Archivos JSON de dashboards
