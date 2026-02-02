# Repositories (infra)

## 🎯 Misión
Implementar los repositorios concretos del dominio sobre Postgres o in‑memory, manteniendo contratos estables para la capa de aplicación.

**Qué SÍ hace**
- Provee repositorios Postgres para documentos, workspaces, usuarios y auditoría.
- Provee repositorios in‑memory para tests y dev.
- Encapsula SQL y mapping de filas a entidades.

**Qué NO hace**
- No contiene reglas de negocio (solo persistencia).
- No expone endpoints HTTP.

**Analogía (opcional)**
- Es el “archivo físico” donde se guardan y recuperan registros.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | Facade de exports de repositorios. |
| 📁 `in_memory/` | Carpeta | Implementaciones en memoria (tests/dev). |
| 📁 `postgres/` | Carpeta | Implementaciones sobre PostgreSQL. |
| 📄 `README.md` | Documento | Esta documentación. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: llamadas desde casos de uso (DocumentRepository, WorkspaceRepository, etc.).
- **Proceso**: SQL parametrizado o estructuras en memoria.
- **Output**: entidades del dominio o valores simples.

Tecnologías/librerías usadas aquí:
- psycopg/pgvector (Postgres), estructuras en memoria (in‑memory).

Flujo típico:
- Use case invoca método del repo.
- Repo Postgres usa `get_pool()` y ejecuta SQL.
- Repo in‑memory retorna estructuras locales.

## 🔗 Conexiones y roles
- Rol arquitectónico: Infrastructure Adapter (persistencia).
- Recibe órdenes de: Application (use cases).
- Llama a: DB pool (`infrastructure/db`), sin dependencia HTTP.
- Contratos y límites: debe respetar Protocols de `app/domain/repositories.py`.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.infrastructure.repositories.postgres import PostgresDocumentRepository

repo = PostgresDocumentRepository()
```

## 🧩 Cómo extender sin romper nada
- Si agregás un método al puerto, actualiza todas las implementaciones.
- Mantén SQL parametrizado y con scope por `workspace_id`.
- Añade tests de integración para repositorios Postgres.
- Evita lógica de negocio en los repositorios.

## 🆘 Troubleshooting
- Síntoma: `relation "..." does not exist` → Causa probable: migraciones pendientes → Mirar `alembic/`.
- Síntoma: resultados vacíos → Causa probable: workspace_id incorrecto → Revisar argumentos.
- Síntoma: errores de pool → Causa probable: `init_pool` faltante → Mirar `infrastructure/db/pool.py`.

## 🔎 Ver también
- [Postgres repos](./postgres/README.md)
- [In-memory repos](./in_memory/README.md)
- [Domain repositories](../../domain/repositories.py)
