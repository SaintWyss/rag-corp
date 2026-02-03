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

- No contiene SQL de negocio. Razón: ** las queries pertenecen a `infrastructure/repositories/`. Impacto: ** si aparece SQL acá, se rompe la separación por capas y se hace difícil testear/mantener.

- No define modelos del dominio. Razón: ** el dominio vive en `app/domain/`. Impacto: ** este módulo se limita a “conectividad e instrumentación”, sin reglas de negocio.

## 🗺️ Mapa del territorio

| Recurso | Tipo | Responsabilidad (en humano) |
| :------------------- | :------------- | :----------------------------------------------------------------------------------------- |
| `__init__.py` | Archivo Python | Exporta el pool y errores públicos para imports estables. |
| `errors.py` | Archivo Python | Errores tipados del pool (no inicializado, doble init, conectividad). |
| `instrumentation.py` | Archivo Python | Wrapper/proxy de conexión/pool: métricas, timings y detección de consultas lentas. |
| `pool.py` | Archivo Python | Inicialización y ciclo de vida del pool singleton (`init_pool`, `get_pool`, `close_pool`). |
| `README.md` | Documento | Portada + guía operativa del pool de DB. |

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
```python
# Por qué: muestra el contrato mínimo del módulo.
from app.infrastructure.db.pool import init_pool, get_pool, close_pool

init_pool(database_url="postgresql://...", min_size=1, max_size=5)
with get_pool().connection() as conn:
    conn.execute("SELECT 1")
close_pool()
```

```python
# Por qué: ejemplo de integración sin infraestructura real.
from app.infrastructure.db.pool import get_pool

with get_pool().connection() as conn:
    conn.execute("SELECT 1")
```

## 🧩 Cómo extender sin romper nada
- Si agregás parámetros de pool, exponerlos en `crosscutting/config.py`.
- Mantener instrumentación dentro de `instrumentation.py`.
- Wiring: init/cierre se hace en `app/api/main.py` y `app/worker/worker.py`.
- Si necesitás exponer el pool a otros componentes, cablealo vía `app/container.py`.
- Tests: integration en `apps/backend/tests/integration/` contra Postgres real.

## 🆘 Troubleshooting
- **Síntoma:** `PoolNotInitializedError`.
- **Causa probable:** no se llamó `init_pool()`.
- **Dónde mirar:** `app/api/main.py` y `app/worker/worker.py`.
- **Solución:** inicializar pool en startup.
- **Síntoma:** `PoolAlreadyInitializedError`.
- **Causa probable:** doble init en tests o reload.
- **Dónde mirar:** `pool.py`.
- **Solución:** cerrar pool en teardown.
- **Síntoma:** `DatabaseConnectionError`.
- **Causa probable:** DB caída o URL inválida.
- **Dónde mirar:** `DATABASE_URL`.
- **Solución:** corregir URL y conexión.
- **Síntoma:** slow queries.
- **Causa probable:** índice faltante.
- **Dónde mirar:** logs y repositorio que ejecuta la query.
- **Solución:** optimizar SQL/índices.

## 🔎 Ver también
- `../repositories/README.md`
- `../../crosscutting/metrics.py`
- `../../api/main.py`
