# Infrastructure Repositories

Implementaciones concretas de los repositorios definidos en la capa de Domain.

## Estructura

```
repositories/
├── __init__.py           # Exports centralizados
├── postgres/             # Implementaciones de producción (PostgreSQL + SQLAlchemy)
│   ├── document.py
│   ├── workspace.py
│   ├── workspace_acl.py
│   ├── audit_event.py
│   └── user.py
└── in_memory/            # Implementaciones para testing/desarrollo
    ├── conversation.py
    ├── workspace.py
    ├── workspace_acl.py
    ├── feedback_repository.py
    └── audit_repository.py
```

## Guía de Uso

### Producción

```python
from app.infrastructure.repositories.postgres import (
    PostgresDocumentRepository,
    PostgresWorkspaceRepository,
    PostgresAuditEventRepository,
)

# Típicamente se usan via el container (DI)
from app.container import get_document_repository

repo = get_document_repository()
```

### Testing

```python
from app.infrastructure.repositories.in_memory import (
    InMemoryConversationRepository,
    InMemoryFeedbackRepository,
    InMemoryAnswerAuditRepository,
)

# Para tests que no necesitan DB real
feedback_repo = InMemoryFeedbackRepository()
feedback_repo.save_vote(conversation_id="conv-1", ...)
```

## Mapeo: Domain Interface → Implementation

| Interface (Domain)         | Production            | Testing              |
| -------------------------- | --------------------- | -------------------- |
| `DocumentRepository`       | `PostgresDocument...` | -                    |
| `WorkspaceRepository`      | `PostgresWorkspace..` | `InMemoryWorkspace.` |
| `WorkspaceAclRepository`   | `PostgresWorkspace..` | `InMemoryWorkspace.` |
| `ConversationRepository`   | -                     | `InMemoryConvers...` |
| `AuditEventRepository`     | `PostgresAuditEv...`  | -                    |
| `FeedbackRepository` 🆕    | (TODO)                | `InMemoryFeedback..` |
| `AnswerAuditRepository` 🆕 | (TODO)                | `InMemoryAnswerAu..` |

## TODOs (Producción)

Los siguientes repositorios tienen interfaz + implementación in-memory, pero **faltan** las implementaciones PostgreSQL:

1. **`PostgresFeedbackRepository`** - Para persistir votos de RLHF
2. **`PostgresAnswerAuditRepository`** - Para persistir logs de auditoría de respuestas

Esquema SQL sugerido en `in_memory/README.md`.

## Principios

1. **Separación por Tecnología:** `postgres/` vs `in_memory/` vs `redis/` (futuro)
2. **Thread Safety:** Las implementaciones in-memory usan `Lock`
3. **Copias Defensivas:** No compartir listas/dicts mutables
4. **Soft Delete:** Preferir `archived_at` / `deleted_at` sobre borrado físico
5. **Naming Corto:** `document.py` en vez de `postgres_document_repository.py`
