# db

Como una **central eléctrica**: entrega conexiones a Postgres de forma segura, medible y reutilizable para todo el backend.

## 🎯 Misión

Este módulo centraliza el **pool de conexiones a Postgres** y su instrumentación (timings, healthchecks y errores tipados). Es el punto único donde se decide **cómo** se crean, reutilizan y cierran conexiones; los repositorios solo consumen el pool.

Recorridos rápidos por intención:

- **Quiero ver el ciclo de vida del pool (init/get/close)** → `pool.py`
- **Quiero ver métricas / slow queries / wrappers** → `instrumentation.py`
- **Quiero ver errores tipados del pool** → `errors.py`
- **Quiero usar el pool desde un repositorio** → snippet “repositorio” abajo

### Qué SÍ hace

- Inicializa y expone un **pool singleton** para todo el proceso.
- Envuelve el pool con instrumentación para **medir latencia** y facilitar diagnóstico.
- Provee utilidades de salud (healthcheck) y errores tipados para fallos previsibles.

### Qué NO hace (y por qué)

- No contiene SQL de negocio.
  - **Razón:** las queries pertenecen a `infrastructure/repositories/`.
  - **Impacto:** si aparece SQL acá, se rompe la separación por capas y se hace difícil testear/mantener.

- No define modelos del dominio.
  - **Razón:** el dominio vive en `app/domain/`.
  - **Impacto:** este módulo se limita a “conectividad e instrumentación”, sin reglas de negocio.

## 🗺️ Mapa del territorio

| Recurso              | Tipo           | Responsabilidad (en humano)                                                                |
| :------------------- | :------------- | :----------------------------------------------------------------------------------------- |
| `__init__.py`        | Archivo Python | Exporta el pool y errores públicos para imports estables.                                  |
| `errors.py`          | Archivo Python | Errores tipados del pool (no inicializado, doble init, conectividad).                      |
| `instrumentation.py` | Archivo Python | Wrapper/proxy de conexión/pool: métricas, timings y detección de consultas lentas.         |
| `pool.py`            | Archivo Python | Inicialización y ciclo de vida del pool singleton (`init_pool`, `get_pool`, `close_pool`). |
| `README.md`          | Documento      | Portada + guía operativa del pool de DB.                                                   |

## ⚙️ ¿Cómo funciona por dentro?

Input → Proceso → Output (sin SQL de negocio).

### 1) Inicialización (startup)

- **Input:** `DATABASE_URL` (o `database_url`) + parámetros del pool (min/max, timeouts, etc.).
- **Proceso:**
  1. `init_pool(...)` valida que el pool no exista (evita dobles inicializaciones).
  2. crea el pool real (driver/pool library) y aplica configuración de conexión.
  3. envuelve el pool con instrumentación (métricas + slow queries) si está habilitada.
  4. guarda el singleton en memoria para `get_pool()`.

- **Output:** un pool listo para ser usado desde repositorios vía `with pool.connection()`.

### 2) Consumo (repositorios)

- **Input:** llamada del repositorio.
- **Proceso:**
  1. `get_pool()` devuelve el singleton (o falla con error tipado si no se inicializó).
  2. el repositorio abre una conexión: `with get_pool().connection() as conn:`.
  3. ejecuta SQL (en el repositorio), y opcionalmente transacciones (`with conn.transaction():`).

- **Output:** filas/resultado hacia Application, con métricas/logs generados por instrumentación.

### 3) Cierre (shutdown)

- **Input:** señal de shutdown (API/worker).
- **Proceso:** `close_pool()` cierra conexiones abiertas y marca el singleton como cerrado.
- **Output:** liberación de recursos sin leaks.

### 4) Healthchecks

- **Input:** invocación de healthcheck (por endpoint `/healthz` o startup).
- **Proceso:** se intenta una conexión corta y una query mínima (ej. `SELECT 1`).
- **Output:** OK/ERROR con diagnóstico acotado (sin filtrar credenciales).

Conceptos mínimos en contexto:

- **Pool de conexiones:** mantiene conexiones reutilizables para evitar overhead de crear/cerrar por request.
- **Instrumentación:** mide latencias y etiqueta resultados; no altera el SQL.

## 🔗 Conexiones y roles

- **Rol arquitectónico:** Infrastructure adapter (DB access / conectividad).

- **Recibe órdenes de:**
  - Bootstrap de API (startup/lifespan).
  - Bootstrap del worker.

- **Llama a:**
  - Librería de pool/driver (ej. `psycopg_pool`) y extensiones/tipos necesarios (ej. pgvector si aplica).
  - `app/crosscutting/metrics.py` para métricas best-effort.

- **Reglas de límites (imports/ownership):**
  - Este módulo no conoce repositorios ni casos de uso.
  - Repositorios consumen el pool; el pool no conoce SQL de negocio.
  - No expone detalles del vendor hacia Domain/Application: solo ofrece un pool listo.

## 👩‍💻 Guía de uso (Snippets)

### 1) Ciclo de vida manual (scripts / pruebas)

```python
from app.infrastructure.db.pool import init_pool, get_pool, close_pool

init_pool(database_url="postgresql://...", min_size=1, max_size=5)

with get_pool().connection() as conn:
    conn.execute("SELECT 1")

close_pool()
```

### 2) Integración en FastAPI (startup/shutdown)

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.crosscutting.config import get_settings
from app.infrastructure.db.pool import init_pool, close_pool

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_pool(
        database_url=settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
    )
    try:
        yield
    finally:
        close_pool()

app = FastAPI(lifespan=lifespan)
```

### 3) Uso en repositorios (patrón recomendado)

```python
from app.infrastructure.db.pool import get_pool

class ExampleRepository:
    def ping(self) -> int:
        with get_pool().connection() as conn:
            row = conn.execute("SELECT 1").fetchone()
            return int(row[0])
```

### 4) Medición por etapas (si el repo captura timings)

```python
from app.crosscutting.timing import StageTimings
from app.infrastructure.db.pool import get_pool

timings = StageTimings()

with timings.measure("db"):
    with get_pool().connection() as conn:
        conn.execute("SELECT 1")

print(timings.to_dict())
```

## 🧩 Cómo extender sin romper nada

Checklist práctico:

1. **Singleton real:** `init_pool()` debe ser idempotente (o fallar con error tipado) y `get_pool()` no debe crear pools implícitos.
2. **Instrumentación en un solo lugar:** cualquier wrapper/metrics va en `instrumentation.py`, no en repositorios.
3. **Errores tipados:** para escenarios previsibles (no init, doble init, conexión fallida), usar excepciones de `errors.py`.
4. **Sin SQL de negocio:** este módulo solo gestiona conectividad; queries y transacciones viven en repos.
5. **Parámetros por settings:** cuando se agregue un parámetro nuevo (timeouts, sslmode, statement timeout), exponerlo vía `crosscutting/config.py`.
6. **Tests:**
   - integration: validar init/close + `SELECT 1` contra Postgres real.
   - unit: wrappers de instrumentación sin conectar a DB (fakes/mocks).

## 🆘 Troubleshooting

- **`PoolNotInitializedError`** → no se llamó `init_pool()` → revisar startup/lifespan (API) o bootstrap (worker) y `pool.py`.
- **`PoolAlreadyInitializedError`** → doble init (tests o reload) → revisar que startup no corra dos veces y que los tests cierren el pool en teardown.
- **`DatabaseConnectionError`** → DB inaccesible / credenciales mal → revisar `DATABASE_URL`, red, puerto y logs del contenedor.
- **TimeOut al obtener conexión** → `max_size` bajo o conexiones colgadas → revisar métricas de pool y ajustar sizes/timeouts.
- **Slow queries reportadas** → índice faltante o query pesada (en repos) → revisar el repositorio que la ejecuta y planes de ejecución (EXPLAIN).
- **Errores de tipo pgvector** → extensión/tipo no disponible en DB → verificar migraciones/extension en Postgres y configuración del entorno.

## 🔎 Ver también

- `../repositories/README.md` (SQL de negocio y repositorios)
- `../../crosscutting/metrics.py` (métricas best-effort)
- `../../crosscutting/timing.py` (StageTimings)
- `../../api/main.py` (startup y composición, si aplica)
