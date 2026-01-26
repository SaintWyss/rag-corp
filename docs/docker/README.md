# Docker (v6) — Guía Operativa / Cheat Sheet

Esta guía existe para que puedas **manejar el stack sin pensar**:

- limpiar y resetear Docker,
- reiniciar servicios,
- levantar **solo Front + Back + DB**,
- levantar **TODO** (pipeline async + storage + observabilidad),
  siempre alineado a la realidad del repo.

> Fuente de verdad de servicios/perfiles: `compose.yaml`.

---

## 🚀 Comandos rápidos (los 4 botones)

### 1) Limpiar / Reset

**Stop normal (no borra datos):**

```bash
docker compose down --remove-orphans
```

**Reset total (borra DB/volúmenes del proyecto):**

```bash
docker compose down -v --remove-orphans
```

**Nuclear (último recurso, afecta TODO Docker en tu máquina):**

```bash
docker compose down -v --remove-orphans
docker system prune -a --volumes --force
```

---

### 2) Reiniciar

**Reiniciar todo lo que esté corriendo (sin bajar):**

```bash
docker compose restart
```

**Reiniciar un servicio puntual:**

```bash
docker compose restart rag-api
# o
docker compose restart worker
```

**Rebuild + restart (cambiaste deps / Dockerfile):**

```bash
docker compose down --remove-orphans
docker compose up -d --build
```

---

### 3) Levantar SOLO Front + Back + DB

> Modo ideal para UI/auth/UX. **No sirve para upload real** (falta worker+redis+storage).

#### Opción recomendada (Front en host)

```bash
pnpm docker:up
pnpm db:migrate
pnpm dev
```

#### Opción “todo en Docker” (Front en contenedor)

```bash
docker compose --profile e2e up -d --build db rag-api web
```

---

### 4) Levantar TODO (pipeline async + storage + observabilidad)

> Modo completo: upload → PENDING → READY → chat con fuentes.

#### Full recomendado (sin Front)

```bash
pnpm stack:full
pnpm db:migrate
```

#### Full + Front (todo en Docker)

```bash
docker compose --profile full --profile e2e up -d --build
pnpm db:migrate
```

---

## 1) Concepto clave: perfiles de Docker Compose

Este repo usa **perfiles** para no levantar todo siempre.

Perfiles (ver `compose.yaml`):

- **Base (default):** `db`, `rag-api`
- **worker:** `worker`, `redis`
- **storage:** `minio`, `minio-init`
- **observability:** `prometheus`, `grafana`, `postgres-exporter`
- **full:** combina `worker + storage + observability`
- **e2e:** `web` (Next.js en contenedor)

Regla práctica:

- Si vas a **subir archivos** necesitás **storage + worker** (y por lo tanto Redis).
- Si solo estás tocando UI / auth / pantallas, podés vivir con **Front + Back + DB**.

---

## 2) Variables mínimas para que upload funcione (modo FULL)

En tu `.env`:

```env
S3_ENDPOINT_URL=http://minio:9000
S3_BUCKET=rag-documents
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin

REDIS_URL=redis://redis:6379
```

---

## 3) URLs útiles

- **Frontend (web):** http://localhost:3000
- **Backend API:** http://localhost:8000
- **Swagger:** http://localhost:8000/docs
- **DB:** localhost:5432
- **MinIO:** http://localhost:9000 (console: 9001)
- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3001

---

## 4) Operaciones diarias

### Logs

```bash
# Todo
docker compose logs -f

# Servicio específico
docker compose logs -f rag-api
docker compose logs -f worker
```

### Estado

```bash
docker compose ps
```

### Entrar a contenedores

```bash
# API
docker compose exec rag-api sh

# DB
docker compose exec db psql -U postgres -d rag
```

---

## 5) Qué hace cada servicio (mini tabla)

| Servicio            | Perfil             |         Puerto | Función                                            |
| ------------------- | ------------------ | -------------: | -------------------------------------------------- |
| `db`                | base               |           5432 | Postgres + pgvector (datos + embeddings)           |
| `rag-api`           | base               |           8000 | Backend FastAPI (auth, workspaces, documents, ask) |
| `web`               | e2e                |           3000 | Next.js en contenedor (útil para E2E/encapsulado)  |
| `redis`             | worker/full        |           6379 | Cola/cache (RQ)                                    |
| `worker`            | worker/full        | 8001 (interno) | Procesa documentos async (PENDING→READY/FAILED)    |
| `minio`             | storage/full       |           9000 | Storage S3 compatible (archivos)                   |
| `minio-init`        | storage/full       |              — | Crea bucket / init de storage                      |
| `prometheus`        | observability/full |           9090 | Métricas                                           |
| `grafana`           | observability/full |           3001 | Dashboards                                         |
| `postgres-exporter` | observability/full |           9187 | Métricas de Postgres                               |

---

## 6) Troubleshooting rápido

### “Port already allocated”

```bash
docker compose down --remove-orphans
```

### Upload se queda en PENDING / falla

Checklist:

1. `worker` levantado (`docker compose ps`)
2. `redis` levantado
3. `.env` con `S3_*` y `REDIS_URL`

Levantar full:

```bash
docker compose --profile full up -d
```

### “File storage unavailable”

Te faltan variables `S3_*` o no levantaste `--profile storage`.

### “Document queue unavailable”

No está Redis/worker (`--profile worker` o `--profile full`).
