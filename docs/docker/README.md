# Docker — Guía completa (RAG Corp)

Esta guía es tu **manual de uso diario** para Docker en RAG Corp: qué es cada contenedor, qué perfiles existen, y qué comandos usar para **levantar / apagar / rebuild / resetear / borrar** sin romper nada.

> **Fuente de verdad:** `compose.yaml` en la raíz del repo.

---

## 0) Modelo mental (simple, como vos lo pensás)

Tu proyecto se divide en 3 “capas” operativas:

1) **Core Full‑Stack (día a día)**
- **DB + API** (y el Front lo corrés en tu host con `pnpm dev`).
- Sirve para: UI, auth, endpoints normales, debug rápido.

2) **RAG / IA (pipeline async real)**
- Agrega: **Redis + Worker + MinIO**.
- Sirve para: upload real, procesamiento de documentos, embeddings, pasar de **PENDING → READY**.

3) **Observability / Diagnóstico (opcional)**
- Agrega: **Prometheus + Grafana + Exporters**.
- Sirve para: métricas, latencias, errores, salud del sistema.

Regla práctica:
- Si tocás UI/auth/endpoints: **Core**.
- Si querés subir docs y que se procesen: **RAG**.
- Si estás debuggeando perf/errores: **Observability**.

---

## 1) Qué hace cada cosa (Worker / Storage / Observability)

### 1.1 Worker (perfil `rag`) — “el que labura cuando subís un PDF”
**Worker** es un proceso separado de la API que ejecuta tareas pesadas en segundo plano.

**Flujo real del sistema (upload):**
1. Subís un archivo.
2. La **API** guarda metadata en DB y marca el documento **PENDING**.
3. La API encola un “job” en **Redis**.
4. El **Worker** toma el job, descarga el archivo (MinIO), hace chunking, genera embeddings, guarda chunks/embeddings y marca **READY** (o **FAILED**).

**Por qué no lo hace la API:**
- La API queda rápida y estable (no se clava con PDFs grandes).
- Podés escalar workers aparte.
- El pipeline es más “production‑like”.

**Cuándo lo necesitás:**
- Cuando querés que el upload funcione “de verdad” y los docs pasen a READY.

---

### 1.2 Redis — “la cola”
Redis se usa como **broker/cola** para jobs.

- La API manda jobs a Redis.
- El worker consume jobs de Redis.

**Cuándo lo necesitás:**
- Siempre que uses worker/pipeline async.

---

### 1.3 Storage (MinIO) — “S3 local”
MinIO es un storage compatible con S3 (como AWS S3, pero local).

**Qué guarda:**
- Los archivos (PDFs, docs) que subís.

**Qué NO guarda:**
- Embeddings/chunks: eso va a Postgres (pgvector).

**Por qué no se guarda en DB:**
- DB no es ideal para archivos grandes.
- S3/MinIO es lo estándar para objetos.

**Cuándo lo necesitás:**
- Cuando quieras subir documentos reales y procesarlos.

---

### 1.4 Observability (Prometheus + Grafana) — “tablero y métricas”
- **Prometheus** recolecta métricas (contadores, latencias, errores, etc.).
- **Grafana** muestra dashboards.

**Cuándo lo necesitás:**
- Cuando algo anda lento, falla, o querés ver el estado real.

---

## 2) Servicios del `compose.yaml` (qué es cada contenedor)

> Esto es “para qué sirve cada docker” en tu repo.

### Core
- `db`: Postgres + pgvector (datos + embeddings)
- `rag-api`: FastAPI (auth, docs, chat, RAG)

### UI (opcional)
- `web`: Next.js en contenedor (útil para E2E o si querés todo dockerizado)

### RAG pipeline (IA)
- `redis`: cola/broker de jobs
- `worker`: procesamiento async (PENDING → READY)
- `minio`: storage tipo S3
- `minio-init`: inicializa bucket/alias en MinIO

### Observability
- `prometheus`: recolección de métricas
- `grafana`: dashboards
- `postgres-exporter`: expone métricas de Postgres a Prometheus

---

## 3) Profiles (cómo “armás” stacks sin volverte loco)

Los `profiles` de Docker Compose te dejan elegir qué conjunto levantar.

### Stacks recomendados (modelo oficial de este repo)

1) **Core** (sin profile)
- Servicios: `db`, `rag-api`
- Para: trabajo diario en back/front, debug rápido.

2) **RAG** (perfil `rag`)
- Servicios extra: `redis`, `worker`, `minio`, `minio-init`
- Para: upload real, procesamiento y embeddings.

3) **Observability** (perfil `observability`)
- Servicios extra: `prometheus`, `grafana`, `postgres-exporter`
- Para: métricas, diagnóstico.

4) **Full** (perfil `full`)
- Combina: `rag` + `observability`

5) **UI en Docker** (perfil `ui` o `e2e`)
- Servicio extra: `web`

---

## 4) Comandos de uso diario (modo “4 botones”)

> Recomendación: usá scripts PNPM para no memorizar flags.

### 4.1 Encender (Up)

**A) Core (DB + API):**
```bash
pnpm stack:core
```

**B) Core + pipeline RAG (upload real):**
```bash
pnpm stack:rag
```

**C) Observability:**
```bash
pnpm stack:obs
```

**D) Todo junto (RAG + observability):**
```bash
pnpm stack:full
```

**E) Todo + UI en Docker (raro pero existe):**
```bash
pnpm stack:all
```

---

### 4.2 Apagar (Stop)

**Stop normal (NO borra datos):**
```bash
pnpm stack:stop
```

---

### 4.3 Rebuild (cuando cambiaste dependencias)

Si tocaste `requirements.txt`, `Dockerfile`, `package.json` del front, o cambios grandes:

```bash
pnpm stack:stop
pnpm stack:core
```

(En los scripts usamos `--build`, así que recompila cuando haga falta.)

---

### 4.4 Reset / Borrado

**Reset del proyecto (borra volúmenes del proyecto = DB/Redis/MinIO):**
```bash
pnpm stack:reset
```

**Nuclear (borra TODO Docker en tu máquina):**
```bash
pnpm stack:nuke
```

⚠️ `stack:nuke` es destructivo: elimina imágenes/volúmenes globales. Usalo solo si Docker quedó hecho un nudo.

---

## 5) Build vs Up (explicado en criollo)

- **Build** = “crear la imagen” (la receta del Dockerfile → imagen).
- **Up** = “correr” los contenedores (imagen → servicio corriendo).

En este repo, para simplificar, casi siempre usamos:
- `docker compose up -d --build ...`

Así vos no pensás: *build si cambió algo, up si no*.

---

## 6) Cómo verificar que todo está bien (estado y salud)

### 6.1 Ver servicios corriendo
```bash
docker compose ps
```

Esperado:
- `db` en **healthy**
- `rag-api` en **healthy**

### 6.2 Ver logs
- DB:
```bash
docker compose logs -f db
```
- API:
```bash
docker compose logs -f rag-api
```
- Worker (si está levantado):
```bash
docker compose logs -f worker
```

---

## 7) Postgres: “no me abría la DB” (guía express)

### 7.1 Entrar a Postgres (desde Docker)
```bash
docker compose exec db psql -U postgres -d rag
```

### 7.2 Conectar desde DBeaver/PGAdmin
- Host: `localhost`
- Port: `5432`
- User: `postgres`
- Password: `postgres`
- Database: `rag`

### 7.3 Errores típicos

**A) Puerto ocupado (5432):**
- Tenés otro Postgres local usando 5432.
- Solución: apagar el Postgres local o cambiar el puerto del servicio `db` en compose.

**B) `db` no está healthy:**
- Mirá logs: `docker compose logs -f db`

---

## 8) ¿Cuándo necesito Worker/Redis/MinIO? (decisión rápida)

Checklist:
- ¿Subís documentos y querés que pasen de PENDING a READY? → **Sí: `pnpm stack:rag`**
- ¿Solo estás tocando UI/auth/chat con mocks o sin upload? → **No: `pnpm stack:core`**

---

## 9) Variables mínimas para “RAG completo”

En tu `.env` (local), para que el pipeline async funcione:

```env
REDIS_URL=redis://redis:6379
S3_ENDPOINT_URL=http://minio:9000
S3_BUCKET=rag-documents
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
```

> Estas defaults están en `.env.example`.

---

## 10) Troubleshooting (rápido)

### 10.1 Upload se queda en PENDING
1) `docker compose ps` → ¿`worker` y `redis` corriendo?
2) ¿`S3_ENDPOINT_URL` y `REDIS_URL` correctos?
3) Levantar pipeline:
```bash
pnpm stack:rag
```

### 10.2 API levanta pero falla con DB
1) `docker compose ps` → DB healthy.
2) Logs:
```bash
docker compose logs -f rag-api
```
3) Validar `DATABASE_URL` interno (en compose): `db:5432`.

### 10.3 Quiero “empezar de cero”
- Reset del proyecto:
```bash
pnpm stack:reset
```

---

## 11) FAQ: dev vs prod (sin meterte quilombo)

- **Dev** = cómodo para programar (reload, volúmenes, debug, iteración rápida).
- **Prod** = “como correría en un servidor real” (más estricto, seguro, sin mounts).

**Hoy:** no necesitás separar en 2 composes. Por eso este repo usa **profiles + scripts**.

Si algún día vas a desplegar en server/K8s, ahí sí conviene separar. Pero no es obligatorio ahora.

---

## 12) Referencias
- `compose.yaml`
- `apps/backend/Dockerfile`
- `apps/frontend/Dockerfile`
- `infra/postgres/init.sql`

