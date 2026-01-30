# 🐳 Docker Cheat Sheet (RAG Corp)

> **Machete de supervivencia.** Copiá y pegá los comandos según lo que necesites hacer hoy.

---

## ✅ 0. Prerrequisitos (1 vez)

- **Node + pnpm** instalados (recomendado: `corepack enable`).
- **Docker Desktop / Docker Engine** corriendo.
- En la raíz del repo:
  - `cp .env.example .env` (si aplica)
  - Configurá `NEXT_PUBLIC_API_URL=http://localhost:8000` si vas a usar el navegador.

> 🧠 Regla de oro: **si el frontend corre en tu PC (browser), la API debe ser `http://localhost:8000`**.

---

## 🚀 1. Rutina diaria

### 🌟 Opción A: Todo en Uno (Recomendado)

Levanta **Backend + Frontend** en una sola terminal.

```bash
pnpm stack:ui
```

_(Acceder en: [http://localhost:3000](http://localhost:3000))_

---

### 🔧 Opción B: Modo Híbrido (Backend Docker + Front Local)

Usá esto si querés que el frontend recargue rápido al editar código (`hot-reloading`).

**Terminal 1 (Infra):**

| Modo     | Comando           | Levanta               | Útil para            |
| -------- | ----------------- | --------------------- | -------------------- |
| **Core** | `pnpm stack:core` | DB + API              | Backend, DB (rápido) |
| **RAG**  | `pnpm stack:rag`  | Core + Worker + MinIO | Uploads reales       |
| **Full** | `pnpm stack:full` | Todo + Grafana        | Métricas             |

**Terminal 2 (Front):**

```bash
pnpm dev
```

---

## 🛑 2. Apagar y limpiar

| Situación     | Comando            | Qué hace                                                   |
| ------------- | ------------------ | ---------------------------------------------------------- |
| Fin del día   | `pnpm stack:stop`  | Apaga contenedores (**no borra datos**)                    |
| Todo roto     | `pnpm stack:reset` | Apaga y **borra volúmenes** (DB/redis/minio)               |
| Todo MUY roto | `pnpm stack:nuke`  | Limpieza agresiva (incluye imágenes). **Usar con cuidado** |

---

## 🛠️ 3. Utils (lo que realmente se usa)

### DB / Migraciones

| Acción              | Comando                |
| ------------------- | ---------------------- |
| Entrar a SQL        | `pnpm db:psql`         |
| Aplicar migraciones | `pnpm db:migrate`      |
| Crear admin (dev)   | `pnpm admin:bootstrap` |

### Logs / Estado

| Acción              | Comando                  |
| ------------------- | ------------------------ |
| Estado de servicios | `pnpm stack:ps`          |
| Logs API            | `pnpm stack:logs:api`    |
| Logs Worker         | `pnpm stack:logs:worker` |
| Logs todo           | `pnpm stack:logs`        |

---

## ❓ 4. Escenarios comunes (FAQ)

### “Cambios en Python no se ven”

- Si cambiaste **código**, debería reflejarse (según tu modo de ejecución).
- Si agregaste/actualizaste dependencias (`requirements.txt`):

```bash
pnpm stack:stop
pnpm stack:core  # incluye --build
```

### “El worker no procesa / los docs no pasan a READY”

Checklist:

1. ¿Levantaste modo RAG?

```bash
pnpm stack:rag
```

2. ¿Redis y worker están `Up/Healthy`?

```bash
pnpm stack:ps
pnpm stack:logs:worker
```

3. ¿MinIO está arriba y el bucket existe?

- Consola: [http://localhost:9001](http://localhost:9001)

### “No puedo loguearme como admin”

Si reseteaste la DB, el usuario se borró:

```bash
pnpm admin:bootstrap
# Crea: admin@local / admin
```

### “El frontend no conecta con el backend”

1. Confirmá API viva:

```bash
pnpm stack:ps
```

2. Confirmá URL pública correcta (browser):

- `NEXT_PUBLIC_API_URL=http://localhost:8000`

> 🧠 Si ponés `http://rag-api:8000` funciona **solo dentro de Docker**, no desde tu navegador.

---

## 🧭 5. Perfiles (modelo mental)

- **Core**: DB + migraciones + API. Rápido y liviano.
- **RAG**: agrega cola (Redis + Worker) + storage (MinIO) para uploads y procesamiento async.
- **Observability**: agrega Prometheus/Grafana para métricas.
- **Full**: RAG + Observability.

---

## 📌 6. Puertos (referencia)

| Servicio         | Puerto | URL                                                      | Credenciales                |
| ---------------- | -----: | -------------------------------------------------------- | --------------------------- |
| Frontend (local) |   3000 | [http://localhost:3000](http://localhost:3000)           | -                           |
| API Docs         |   8000 | [http://localhost:8000/docs](http://localhost:8000/docs) | -                           |
| MinIO Console    |   9001 | [http://localhost:9001](http://localhost:9001)           | `minioadmin` / `minioadmin` |
| Grafana          |   3001 | [http://localhost:3001](http://localhost:3001)           | `admin` / `admin`           |
| Postgres         |   5432 | localhost:5432                                           | `postgres` / `postgres`     |

---

## 🔎 7. Diagnóstico rápido (cuando algo “no anda”)

1. **Estado**: `pnpm stack:ps`
2. **Logs**: `pnpm stack:logs:api` / `pnpm stack:logs:worker`
3. **Rebuild** (si cambiaste deps): `pnpm stack:stop && pnpm stack:core`
4. **Reset total** (si DB quedó inconsistente): `pnpm stack:reset && pnpm stack:core`
