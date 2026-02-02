# Repositories Postgres

## 🎯 Misión
Implementar repositorios del dominio sobre PostgreSQL usando psycopg y pgvector.

**Qué SÍ hace**
- Persiste documentos, chunks, workspaces, usuarios y auditoría.
- Ejecuta búsqueda vectorial (similarity/MMR) para RAG.
- Mantiene el scoping por `workspace_id` para seguridad.

**Qué NO hace**
- No define reglas de negocio ni autorización.
- No expone endpoints HTTP.

**Analogía (opcional)**
- Es el “almacén” físico con un índice vectorial incorporado.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | Exports de repositorios Postgres. |
| 🐍 `audit_event.py` | Archivo Python | Persistencia de eventos de auditoría. |
| 🐍 `document.py` | Archivo Python | Documentos + chunks + búsqueda vectorial. |
| 📄 `README.md` | Documento | Esta documentación. |
| 🐍 `user.py` | Archivo Python | CRUD de usuarios para auth/JWT. |
| 🐍 `workspace.py` | Archivo Python | Persistencia de workspaces. |
| 🐍 `workspace_acl.py` | Archivo Python | ACL de workspaces compartidos. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: métodos del repositorio llamados por casos de uso.
- **Proceso**: SQL parametrizado + pgvector para similitud.
- **Output**: entidades de dominio o resultados simples.

Tecnologías/librerías usadas aquí:
- psycopg, pgvector, numpy (para embeddings en queries).

Flujo típico:
- `PostgresDocumentRepository.find_similar_chunks()` ejecuta búsqueda vectorial.
- `PostgresWorkspaceRepository` CRUD de workspaces.
- `user.py` soporta login/admin de usuarios.

## 🔗 Conexiones y roles
- Rol arquitectónico: Infrastructure Adapter (DB).
- Recibe órdenes de: Application (use cases) y Identity (auth_users).
- Llama a: `infrastructure/db/pool.get_pool()`.
- Contratos y límites: no aplica policy; solo persistencia y mapping.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.infrastructure.repositories.postgres import PostgresWorkspaceRepository

repo = PostgresWorkspaceRepository()
```

## 🧩 Cómo extender sin romper nada
- Mantén queries con scope por `workspace_id`.
- No interpolar strings: usa parámetros.
- Si agregas columnas, actualiza el mapping `_row_to_*`.
- Añade migración y tests de integración.

## 🆘 Troubleshooting
- Síntoma: errores de `pgvector` → Causa probable: extensión no instalada → Revisar migraciones de DB.
- Síntoma: resultados duplicados → Causa probable: join incorrecto → Revisar SQL en `document.py`.
- Síntoma: `UndefinedTable` → Causa probable: migraciones faltantes → Ejecutar Alembic.

## 🔎 Ver también
- [DB pool](../../db/README.md)
- [Domain repositories](../../../domain/repositories.py)
- [In-memory repos](../in_memory/README.md)
