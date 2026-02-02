# Infrastructure DB

## 🎯 Misión
Centralizar el pool de conexiones a Postgres y su instrumentación (timings, healthchecks y errores tipados).

**Qué SÍ hace**
- Inicializa y expone un pool singleton.
- Instrumenta consultas para métricas y logs.
- Define errores claros de pool/conectividad.

**Qué NO hace**
- No contiene SQL de negocio (eso está en repositorios).
- No define modelos de dominio.

**Analogía (opcional)**
- Es la “central eléctrica” que entrega conexiones seguras y medibles.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | Exports del pool y errores. |
| 🐍 `errors.py` | Archivo Python | Errores tipados del pool DB. |
| 🐍 `instrumentation.py` | Archivo Python | Proxy de conexión con métricas/slow queries. |
| 🐍 `pool.py` | Archivo Python | Inicialización y ciclo de vida del pool. |
| 📄 `README.md` | Documento | Esta documentación. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: `DATABASE_URL` y parámetros de pool.
- **Proceso**: `init_pool()` crea el pool real y lo envuelve con instrumentación.
- **Output**: `get_pool()` devuelve un pool listo para `with pool.connection()`.

Tecnologías/librerías usadas aquí:
- psycopg_pool, pgvector, métricas en `crosscutting/metrics`.

Flujo típico:
- La API llama `init_pool()` en startup.
- Repositorios usan `get_pool()` y ejecutan SQL.
- `InstrumentedConnectionPool` mide latencia y hace healthcheck opcional.

## 🔗 Conexiones y roles
- Rol arquitectónico: Infrastructure Adapter (DB access).
- Recibe órdenes de: API startup/worker bootstrap.
- Llama a: psycopg_pool, pgvector, métricas.
- Contratos y límites: no contiene queries de negocio.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.infrastructure.db.pool import init_pool, get_pool, close_pool

init_pool(database_url="postgresql://...", min_size=1, max_size=5)
with get_pool().connection() as conn:
    conn.execute("SELECT 1")
close_pool()
```

## 🧩 Cómo extender sin romper nada
- Mantén el pool como singleton; evita múltiples inits.
- Si agregas instrumentación, hazla en `instrumentation.py`.
- No mezcles SQL de negocio aquí.
- Agrega tests de integración si cambias la inicialización.

## 🆘 Troubleshooting
- Síntoma: `PoolNotInitializedError` → Causa probable: no se llamó `init_pool()` → Mirar `pool.py`.
- Síntoma: `PoolAlreadyInitializedError` → Causa probable: doble init → Revisar startup.
- Síntoma: `DatabaseConnectionError` → Causa probable: DB inaccesible → Revisar `DATABASE_URL`.

## 🔎 Ver también
- [Repositories](../repositories/README.md)
- [Crosscutting metrics](../../crosscutting/metrics.py)
