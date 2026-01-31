# PostgreSQL Repositories

Implementaciones de producción de los repositorios del dominio usando SQLAlchemy y PostgreSQL.

## Estructura

```
postgres/
├── __init__.py       # Exports públicos
├── document.py       # PostgresDocumentRepository (Chunks + Vectors)
├── workspace.py      # PostgresWorkspaceRepository
├── workspace_acl.py  # PostgresWorkspaceAclRepository
├── audit_event.py    # PostgresAuditEventRepository
└── user.py           # Funciones de usuario (legacy functions)
```

## Repositorios

### PostgresDocumentRepository

El repositorio más complejo. Maneja:

- CRUD de documentos
- Almacenamiento de chunks con embeddings (pgvector)
- Búsqueda semántica (`find_similar_chunks`)
- Soft delete con `deleted_at`
- Estados de procesamiento (`pending`, `processing`, `ready`, `error`)

```python
from app.infrastructure.repositories.postgres import PostgresDocumentRepository

repo = PostgresDocumentRepository()

# Guardar documento + chunks atómicamente
repo.save_document_with_chunks_atomic(document, chunks, workspace_id)

# Búsqueda semántica
similar = repo.find_similar_chunks(embedding, workspace_id, top_k=5)
```

### PostgresWorkspaceRepository

CRUD de workspaces con:

- Visibilidad (PRIVATE, ORG_READ, SHARED)
- Soft delete (archived_at)
- Filtros por owner

```python
from app.infrastructure.repositories.postgres import PostgresWorkspaceRepository

repo = PostgresWorkspaceRepository()

# Listar workspaces visibles para un usuario
workspaces = repo.list_workspaces_visible_to_user(user_id)
```

### PostgresWorkspaceAclRepository

Manejo de ACL para workspaces compartidos:

- Lista de usuarios con acceso a un workspace
- Reverse lookup: workspaces accesibles por un usuario

### PostgresAuditEventRepository

Registro de eventos de auditoría del sistema:

- Login/logout
- Cambios de configuración
- Acciones administrativas

### User Functions (Legacy)

El archivo `user.py` contiene funciones standalone (no clase) para manejo de usuarios.
**Nota:** Sería buena práctica refactorizarlo a una clase `PostgresUserRepository`.

## Patrones Utilizados

### 1. Session Management

Cada método obtiene su propia sesión y la cierra:

```python
def get_document(self, document_id: UUID) -> Document | None:
    from ....infrastructure.db.pool import get_session

    session = get_session()
    try:
        # ... query
    finally:
        session.close()
```

### 2. Error Handling Centralizado

Usa helpers de `crosscutting.exceptions`:

```python
from ....crosscutting.exceptions import DatabaseError

try:
    # ... operación
except SQLAlchemyError as e:
    raise DatabaseError("Descripción", original_error=e)
```

### 3. Soft Delete

Todos los repositorios con datos importantes usan soft delete:

```python
# No se borra realmente
document.deleted_at = datetime.now(UTC)
```

## Extensibilidad

Para agregar un nuevo repositorio PostgreSQL:

1. Crear archivo en `postgres/` (ej: `postgres/feedback.py`)
2. Implementar la interfaz del `domain/repositories.py`
3. Exportar en `postgres/__init__.py`
4. Agregar factory en `container.py`

## Migraciones

Las tablas se manejan con Alembic. Ver `/alembic/versions/` para el historial.
