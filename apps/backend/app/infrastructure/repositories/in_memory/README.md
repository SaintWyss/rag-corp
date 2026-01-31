# In-Memory Repositories

Implementaciones en memoria de los repositorios del dominio para **testing** y **desarrollo local**.

## ⚠️ NO APTO PARA PRODUCCIÓN

Estas implementaciones:

- **Pierden datos** cuando el proceso se reinicia
- **No son thread-safe** para múltiples workers
- **No tienen persistencia**

## Uso

### Testing

```python
from app.infrastructure.repositories.in_memory import (
    InMemoryFeedbackRepository,
    InMemoryAnswerAuditRepository,
)

def test_vote_answer():
    feedback_repo = InMemoryFeedbackRepository()

    vote_id = feedback_repo.save_vote(
        conversation_id="conv-123",
        message_index=0,
        user_id=uuid4(),
        vote="up",
    )

    assert vote_id.startswith("vote-")

    # Cleanup
    feedback_repo.clear()
```

### Desarrollo Local

```python
# En el composition root (main.py o similar)
from app.infrastructure.repositories.in_memory import (
    InMemoryFeedbackRepository,
    InMemoryAnswerAuditRepository,
)

if settings.environment == "development":
    feedback_repo = InMemoryFeedbackRepository()
    audit_repo = InMemoryAnswerAuditRepository()
else:
    feedback_repo = PostgresFeedbackRepository(db)
    audit_repo = PostgresAnswerAuditRepository(db)
```

## Repositorios Disponibles

### InMemoryFeedbackRepository

| Método                             | Descripción                       |
| ---------------------------------- | --------------------------------- |
| `save_vote(...)`                   | Guarda un voto (idempotente)      |
| `get_vote(...)`                    | Obtiene voto existente            |
| `list_votes_for_conversation(...)` | Lista votos de una conversación   |
| `count_votes(...)`                 | Cuenta votos por tipo             |
| `clear()`                          | Limpia todos los datos (testing)  |
| `get_all_votes()`                  | Obtiene todos los votos (testing) |

### InMemoryAnswerAuditRepository

| Método                        | Descripción                      |
| ----------------------------- | -------------------------------- |
| `save_audit_record(...)`      | Guarda registro de auditoría     |
| `get_audit_record(record_id)` | Obtiene registro por ID          |
| `list_audit_records(...)`     | Lista con filtros                |
| `list_high_risk_records(...)` | Lista solo high-risk             |
| `update_rating(...)`          | Actualiza rating de feedback     |
| `clear()`                     | Limpia todos los datos (testing) |
| `get_all_records()`           | Obtiene todos (testing)          |
| `count_by_confidence()`       | Cuenta por nivel de confianza    |

## Implementaciones Postgres (TODO)

Para producción, implementar:

- `PostgresFeedbackRepository` en `infrastructure/repositories/postgres/`
- `PostgresAnswerAuditRepository` en `infrastructure/repositories/postgres/`

Esquema sugerido:

```sql
CREATE TABLE feedback_votes (
    vote_id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    message_index INT NOT NULL,
    user_id UUID NOT NULL,
    vote TEXT NOT NULL CHECK (vote IN ('up', 'down', 'neutral')),
    comment TEXT,
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (conversation_id, message_index, user_id)
);

CREATE TABLE answer_audit_records (
    record_id TEXT PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    user_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    query TEXT NOT NULL,
    answer_preview TEXT NOT NULL,
    confidence_level TEXT NOT NULL,
    confidence_value FLOAT NOT NULL,
    requires_verification BOOLEAN DEFAULT FALSE,
    sources_count INT NOT NULL,
    source_documents TEXT[],
    user_email TEXT,
    suggested_department TEXT,
    conversation_id TEXT,
    session_id TEXT,
    ip_address TEXT,
    user_agent TEXT,
    response_time_ms INT,
    was_rated BOOLEAN DEFAULT FALSE,
    rating TEXT,
    is_high_risk BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_audit_workspace ON answer_audit_records(workspace_id);
CREATE INDEX idx_audit_user ON answer_audit_records(user_id);
CREATE INDEX idx_audit_high_risk ON answer_audit_records(is_high_risk) WHERE is_high_risk = TRUE;
CREATE INDEX idx_audit_timestamp ON answer_audit_records(timestamp DESC);
```
