# Infra: Database (PostgreSQL Setup)

## 🎯 Misión

Maneja la **conexión física** con la base de datos PostgreSQL.
Responsable de iniciar y terminar el Pool de conexiones (Connection Pooling) y proveer sesiones a los repositorios.

**Qué SÍ hace:**

- Inicializa `psycopg_pool`.
- Gestiona transacciones y sesiones.
- Implementa instrumentación (tracing de SQL).

**Qué NO hace:**

- No define tablas (eso va en Repositorios o Alembic).
- No ejecuta queries de negocio.

**Analogía:**
Es la Central Telefónica. No habla con nadie, pero conecta las llamadas de los repositorios hacia la base de datos.

## 🗺️ Mapa del territorio

| Recurso              | Tipo       | Responsabilidad (en humano)                                    |
| :------------------- | :--------- | :------------------------------------------------------------- |
| `errors.py`          | 🐍 Archivo | Mapeo de errores de DB (UniqueViolation) a excepciones de App. |
| `instrumentation.py` | 🐍 Archivo | Hooks de OpenTelemetry para trazar queries.                    |
| `pool.py`            | 🐍 Archivo | **Singleton**. Crea y gestiona el Pool de conexiones.          |

## ⚙️ ¿Cómo funciona por dentro?

### Connection Pooling (`pool.py`)

Usamos `psycopg_pool.AsyncConnectionPool`.

1.  `init_pool(dsn)`: Se llama al inicio de la app (`main.py`).
2.  `get_session()`: Entrega una conexión del pool.
3.  `close_pool()`: Cierra conexiones al apagar la app.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Infrastructure Low-level mechanics.
- **Recibe órdenes de:** `main.py` (init) y Repositorios (get connection).
- **Llama a:** Driver `psycopg`.

## 👩‍💻 Guía de uso (Snippets)

### Obtener una sesión (Low level)

```python
from app.infrastructure.db.pool import get_session

async with get_session() as conn:
    await conn.execute("SELECT 1")
```

## 🧩 Cómo extender sin romper nada

1.  **Configuración:** Los parámetros del pool (min/max size) vienen de `crosscutting.config`.

## 🆘 Troubleshooting

- **Síntoma:** "Pool not initialized".
  - **Causa:** Intentaste usar la DB antes de que `main.py` llamara a `init_pool` (común en tests unitarios mal aislados).

## 🔎 Ver también

- [Repositorios Postgres](../repositories/postgres/README.md)
