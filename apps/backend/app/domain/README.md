# Domain Layer (Core Business Logic)

Esta capa contiene la **lógica de negocio pura** de la aplicación. Es independiente de frameworks, bases de datos y tecnologías externas.

## Estructura

```
domain/
├── entities.py           # Entidades del dominio
├── repositories.py       # Interfaces de persistencia (Ports)
├── services.py           # Interfaces de servicios (Ports)
├── value_objects.py      # Objetos de valor inmutables 🆕
├── workspace_policy.py   # Políticas de acceso a workspaces
├── audit.py              # Entidades de auditoría
└── __init__.py           # Exports públicos
```

## Componentes

### 1. Entities (`entities.py`)

Entidades con identidad que representan conceptos de negocio.

| Entidad               | Descripción                                                   |
| --------------------- | ------------------------------------------------------------- |
| `Document`            | Documento subido al sistema                                   |
| `Chunk`               | Fragmento de documento con embedding                          |
| `QueryResult`         | Resultado de una consulta RAG (answer + sources + confidence) |
| `ConversationMessage` | Mensaje en una conversación                                   |
| `Workspace`           | Espacio de trabajo aislado                                    |

### 2. Value Objects (`value_objects.py`) 🆕

Objetos inmutables sin identidad propia, iguales si sus atributos son iguales.

#### SourceReference (Citas Estructuradas)

```python
source = SourceReference(
    index=1,
    document_title="Manual de RRHH",
    snippet="La política de vacaciones establece...",
    relevance_score=0.85,
    page_number=12,
)
# Para renderizar "chips" clickeables en el frontend
```

#### ConfidenceScore (Confianza Empresarial) 🆕

```python
confidence = calculate_confidence(
    chunks_used=3,
    chunks_available=5,
    response_length=250,
    topic_category="finance",  # Sugiere "Finanzas" para verificación
)

# confidence.level = "high"
# confidence.display_message = "Respuesta basada en múltiples fuentes verificadas."
# confidence.requires_verification = False
# confidence.suggested_department = "Finanzas"
```

**Niveles de Confianza:**

| Nivel    | Score    | Mensaje para Usuario                                                |
| -------- | -------- | ------------------------------------------------------------------- |
| `high`   | ≥0.8     | "Respuesta basada en múltiples fuentes verificadas."                |
| `medium` | 0.5-0.79 | "Respuesta parcial. Se recomienda verificar."                       |
| `low`    | <0.5     | "Información limitada. Consultar directamente con un especialista." |

**Factores del Score:**

- `chunk_coverage`: Proporción de chunks usados
- `response_completeness`: Longitud de la respuesta
- `keyword_match`: Si hubo match exacto
- `source_freshness`: Antigüedad de las fuentes

#### MetadataFilter (Filtros de Retrieval)

```python
filter = MetadataFilter(
    field="department",
    operator="eq",  # eq, ne, gt, lt, gte, lte, in, contains
    value="legal",
)
```

#### UsageQuota (Rate Limiting)

```python
quota = UsageQuota(limit=100, used=45, resource="messages")
# quota.remaining = 55
# quota.is_exceeded = False
# quota.usage_percentage = 45.0
```

#### FeedbackVote (RLHF)

```python
vote = FeedbackVote(
    vote="up",  # "up", "down", "neutral"
    comment="Excelente respuesta!",
    tags=("accurate", "helpful"),
)
```

#### AnswerAuditRecord (Compliance Empresarial) 🆕

```python
audit = AnswerAuditRecord(
    record_id="audit-001",
    timestamp="2026-01-31T12:00:00Z",
    user_id=user_id,
    workspace_id=workspace_id,
    query="¿Cuál es la política de vacaciones?",
    answer_preview="La política establece...",
    confidence_level="high",
    confidence_value=0.85,
    requires_verification=False,
    sources_count=3,
    suggested_department="RRHH",
)

# audit.is_high_risk = False  # True si confianza baja o pocas fuentes
# audit.audit_summary = "[timestamp] User=email Query='...' Confidence=high Sources=3"
```

### 3. Repository Interfaces (`repositories.py`)

Puertos (Ports) para inyección de dependencias. Las implementaciones están en `infrastructure/`.

| Interface                  | Responsabilidad                                 |
| -------------------------- | ----------------------------------------------- |
| `DocumentRepository`       | CRUD de documentos y chunks, búsqueda vectorial |
| `WorkspaceRepository`      | CRUD de workspaces                              |
| `WorkspaceAclRepository`   | ACL para workspaces compartidos                 |
| `ConversationRepository`   | Historial de conversaciones                     |
| `AuditEventRepository`     | Eventos de auditoría del sistema                |
| `FeedbackRepository` 🆕    | Votos de feedback (RLHF)                        |
| `AnswerAuditRepository` 🆕 | Registros de auditoría de respuestas            |

### 4. Service Interfaces (`services.py`)

Puertos para servicios externos (LLM, Embeddings, etc.)

| Interface            | Responsabilidad              |
| -------------------- | ---------------------------- |
| `EmbeddingService`   | Generar embeddings de texto  |
| `LLMService`         | Generar respuestas con LLM   |
| `TextChunkerService` | Dividir documentos en chunks |

## Principios

1. **Sin Dependencias Externas:** Esta capa NO importa nada de `infrastructure/`.
2. **Inmutabilidad:** Los Value Objects son `frozen=True`.
3. **Validación en Constructor:** Los value objects validan en `__post_init__`.
4. **Serialización Explícita:** Cada value object tiene `to_dict()`.
5. **Equality por Valor:** Dos value objects son iguales si sus atributos son iguales.

## Exports Públicos (`__init__.py`)

```python
from app.domain import (
    # Entities
    Document, Chunk, QueryResult, ConversationMessage,

    # Repository Interfaces
    DocumentRepository, WorkspaceRepository, WorkspaceAclRepository,
    ConversationRepository, AuditEventRepository,
    FeedbackRepository, AnswerAuditRepository,

    # Service Interfaces
    EmbeddingService, LLMService, TextChunkerService,

    # Value Objects
    SourceReference, ConfidenceScore, calculate_confidence,
    MetadataFilter, UsageQuota, FeedbackVote, AnswerAuditRecord,
)
```

## Cómo extender

### Agregar un nuevo Value Object:

1. Añadir en `value_objects.py` con `@dataclass(frozen=True, slots=True)`
2. Implementar `to_dict()` para serialización
3. Exportar en `__init__.py`

### Agregar un nuevo Repository Interface:

1. Añadir en `repositories.py` como `Protocol`
2. Documentar cada método
3. Exportar en `__init__.py`
4. Implementar en `infrastructure/repositories/`

---

**Nota:** La capa Domain es el corazón de la aplicación. Cambios aquí impactan a toda la capa de Application. Proceder con cuidado y tests.
