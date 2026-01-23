# Guía de Docker y Operaciones (Cheat Sheet)

Guía de referencia para operar el stack de desarrollo local de RAG Corp.

## 🚀 Comandos Rápidos (Top 5)

| Acción | Comando |
|:---|:---|
| **Levantar Todo** (Full) | `pnpm stack:full` |
| **Ver Logs** (Tiempo real) | `docker compose logs -f` |
| **Apagar todo** | `docker compose down` |
| **Apagar y borrar datos** | `docker compose down -v` |
| **Reiniciar un servicio** | `docker compose restart <service>` |

---

## 🛠 Escenarios de Trabajo

Elige el comando según qué parte del sistema vas a tocar.

### A. Stack Completo (Recomendado)
Levanta **TODO**: API, DB, Frontend, Worker, Redis y MinIO.
```bash
pnpm stack:full
```
- **Uso**: Pruebas de integración, subir archivos PDF (RAG), testear flujo completo.
- **URLs**:
  - Frontend: `http://localhost:3000`
  - API: `http://localhost:8000/docs`
  - MinIO Consola: `http://localhost:9001` (user/pass: `minioadmin`)

### B. Stack Ligero (UI/UX Only)
Levanta solo **Frontend, API y DB**.
```bash
docker compose up -d rag-api web db
```
- **Uso**: Cambios visuales en Frontend, lógica simple de API (login, usuarios).
- **Limitación**: **NO subas archivos**. Se quedarán en estado `PENDING` porque el Worker está apagado.

### C. Backend Only (API Logic)
Levanta solo **API y DB**.
```bash
pnpm docker:up
```
- **Uso**: Desarrollar endpoints, migraciones de base de datos, unit tests de backend.

---

## 🔍 Operaciones Diarias

### Ver Logs
Ver logs de **todos** los servicios mezclados:
```bash
docker compose logs -f
```
Ver logs de **un servicio específico** (ej: worker o api):
```bash
docker compose logs -f worker
docker compose logs -f rag-api
```

### Entrar a un contenedor (Shell)
Para ejecutar comandos dentro (ej: ver archivos, ejecutar scripts de python manuales):
```bash
# Entrar a la API
docker compose exec rag-api sh

# Entrar a la Base de Datos
docker compose exec db psql -U postgres -d rag
```

### Reiniciar Servicios
Si cambiaste código en Python y no se recarga, o el worker se trabó:
```bash
docker compose restart rag-api
docker compose restart worker
```

---

## 🧹 Mantenimiento y Limpieza

### Limpieza Estándar (Borrar Contenedores)
Simplemente apaga el sistema.
```bash
docker compose down
```

### Limpieza Profunda ("Borrón y Cuenta Nueva")
Borra contenedores y **Volúmenes** (Base de datos se resetea a cero).
```bash
docker compose down -v
```

### Opción "Nuclear" (Problemas graves de Docker)
Si Docker da errores extraños, usa esto para limpiar **todo** (imágenes, caché, redes).
```bash
docker compose down -v --remove-orphans
docker system prune -a --volumes --force
```

---

## 🏗 Arquitectura de Servicios

Breve explicación de qué hace cada pieza:

| Servicio | Puerto | Descripción |
|:---|:---|:---|
| **rag-api** | `8000` | **Backend**. FastAPI. Recibe peticiones HTTP. |
| **web** | `3000` | **Frontend**. Next.js. La interfaz de usuario. |
| **db** | `5432` | **Postgres**. Guarda datos y vectores (pgvector). |
| **worker** | N/A | **Procesador**. Python+RQ. Procesa PDFs en segundo plano. |
| **redis** | `6379` | **Cola**. Mensajería entre API y Worker. |
| **minio** | `9000` | **S3**. Almacenamiento de archivos físicos. |

---

## 🚑 Solución de Problemas (Troubleshooting)

**Error: "Bind for 0.0.0.0:8000 failed: port is already allocated"**
Significa que hay otro proceso (o un docker viejo) usando el puerto.
*Solución*:
```bash
docker rm -f $(docker ps -aq)
```

**Error: Subida de archivos se queda en "PENDING"**
Seguramente levantaste el stack ligero sin Worker.
*Solución*: Levanta el stack completo: `pnpm stack:full`.

**Error: DB password authentication failed**
A veces pasa si cambias el `.env` pero el volumen de la DB ya existe con la clave vieja.
*Solución*: Borra el volumen: `docker compose down -v` y vuelve a levantar.
