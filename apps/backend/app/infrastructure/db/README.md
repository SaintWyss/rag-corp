# Infrastructure DB Layer

## 🎯 Propósito y Rol

Este paquete (`infrastructure/db`) gestiona la conexión física con **PostgreSQL**.
Nuestra prioridad aquí es la **estabilidad, observabilidad y performance**. No implementa lógica de queries (eso va en `repositories`), solo la plomería de conexiones.

---

## 🧩 Componentes Principales

| Archivo              | Rol            | Descripción                                                                                       |
| :------------------- | :------------- | :------------------------------------------------------------------------------------------------ |
| `pool.py`            | **Singleton**  | Gestiona el ciclo de vida del `ConnectionPool`. Configura `pgvector` y timeouts automáticamente.  |
| `instrumentation.py` | **Proxy**      | Envuelve las conexiones para medir tiempos de ejecución (`slow queries`) y realizar healthchecks. |
| `errors.py`          | **Exceptions** | Errores tipados (`PoolNotInitializedError`) para evitar fallos genéricos runtime.                 |

---

## 🛠️ Features "Enterprise"

### 1. Instrumentación Transparente

Implementamos un Proxy Pattern (`InstrumentedConnectionPool`).

- **Qué hace**: Intercepta cada `execute()`.
- **Beneficio**: Si una query tarda más de `DB_SLOW_QUERY_SECONDS` (default 0.25s), se loguea un warning con el tipo de query.
- **Transparencia**: Los repositorios no saben que están siendo monitoreados.

### 2. Configuración Automática de Conexión

Cada vez que se adquiere una conexión:

- Se registra el tipo `vector` (para embeddings).
- Se aplica `statement_timeout` (para evitar queries zombies que cuelguen la DB).

### 3. Fail-Fast

El pool valida su estado. Si intentas usar `get_pool()` sin haber llamado `init_pool()` en el arranque (`main.py`), lanza `PoolNotInitializedError` inmediatamente.

---

## 🚀 Guía de Uso

```python
# Inicialización (al arranque de la app)
init_pool(dsn="postgresql://...", min_size=5, max_size=20)

# Uso en Repositorio
try:
    with get_pool().connection() as conn:
        conn.execute("SELECT 1")
except DatabaseConnectionError:
    # Manejo de error de conexión
    ...
```
