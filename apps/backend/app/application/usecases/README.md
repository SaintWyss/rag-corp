# Use Cases (Business Operations)

Esta carpeta contiene los **Casos de Uso** de la aplicación. Cada caso de uso representa una **acción de negocio completa** que un usuario (humano o sistema) puede ejecutar.

## Estructura por Feature

```
usecases/
├── chat/                  # Interacción conversacional RAG
│   ├── answer_query.py           # RAG Q&A sincrónico
│   ├── stream_answer_query.py    # RAG con streaming de tokens 🆕
│   ├── answer_query_with_history.py  # RAG + contexto conversacional
│   ├── search_chunks.py          # Búsqueda semántica pura
│   ├── create_conversation.py    # Iniciar sesión de chat
│   ├── get_conversation_history.py  # Recuperar mensajes
│   ├── clear_conversation.py     # Limpiar historial
│   ├── vote_answer.py            # Feedback RLHF (👍/👎) 🆕
│   ├── record_answer_audit.py    # Auditoría compliance 🆕
│   └── chat_utils.py             # Helpers de formateo
│
├── ingestion/             # Pipeline de documentos
│   ├── upload_document.py         # Subir archivo a storage
│   ├── get_document_status.py     # Estado de procesamiento
│   ├── cancel_document_processing.py  # Cancelar docs atascados
│   ├── ingest_document.py         # Orquestar: parse → chunk → embed
│   ├── process_uploaded_document.py  # Worker async
│   └── reprocess_document.py      # Re-embedear un doc existente
│
├── documents/             # CRUD de documentos
│   ├── get_document.py           # Obtener por ID
│   ├── list_documents.py         # Listar por workspace
│   ├── download_document.py      # Descargar archivo
│   ├── delete_document.py        # Eliminar doc + chunks
│   └── document_results.py       # DTOs de respuesta
│
└── workspace/             # Gestión de espacios de trabajo
    ├── create_workspace.py       # Crear nuevo
    ├── get_workspace.py          # Obtener por ID
    ├── list_workspaces.py        # Listar (owner/shared)
    ├── update_workspace.py       # Actualizar metadata
    ├── archive_workspace.py      # Soft-delete
    ├── publish_workspace.py      # Cambiar visibilidad
    ├── share_workspace.py        # Compartir con usuarios
    ├── workspace_access.py       # Verificar permisos
    └── workspace_results.py      # DTOs de respuesta
```

## Features Nuevos 🆕

### Streaming de Respuestas (`stream_answer_query.py`)

```python
from app.application.usecases.chat import StreamAnswerQueryUseCase, StreamChunk

for chunk in use_case.execute(input_data):
    if chunk.type == "token":
        print(chunk.content, end="")  # Efecto "máquina de escribir"
    elif chunk.type == "sources":
        render_sources(chunk.sources)  # Lista de SourceReference
    elif chunk.type == "done":
        show_confidence(chunk.confidence)  # ConfidenceScore
```

### Feedback RLHF (`vote_answer.py`)

```python
from app.application.usecases.chat import VoteAnswerUseCase, VoteAnswerInput

result = use_case.execute(VoteAnswerInput(
    conversation_id="conv-123",
    message_index=2,
    vote="up",  # "up", "down", "neutral"
    comment="Excelente respuesta!",
    tags=["accurate", "helpful"],
    actor=actor,
))
# result.vote_id = "vote-abc123"
```

### Auditoría Empresarial (`record_answer_audit.py`)

```python
from app.application.usecases.chat import RecordAnswerAuditUseCase, RecordAnswerAuditInput

result = use_case.execute(RecordAnswerAuditInput(
    user_id=user_id,
    workspace_id=workspace_id,
    query="¿Cuál es la política de vacaciones?",
    answer="La política establece...",
    confidence_level="high",
    confidence_value=0.85,
    sources_count=3,
    requires_verification=False,
    suggested_department="RRHH",
))
# result.audit_record.is_high_risk = False
```

## Flujo de Trabajo (Pipelines)

### 1. Ingestion Pipeline

```
Usuario sube PDF
       ↓
  upload_document.py
       ↓ (guarda en storage, crea registro pending)
  process_uploaded_document.py (Worker/Queue)
       ↓
  ingest_document.py
       ↓ (parse → chunk → embed)
  Chunks guardados en Vector DB
```

### 2. Chat Pipeline (Sincrónico)

```
Usuario pregunta
       ↓
  answer_query_with_history.py
       ↓ (recupera historial, formatea contexto)
  answer_query.py
       ↓ (embed query → search → build context → LLM)
  Respuesta con citas [S#] + ConfidenceScore
       ↓
  record_answer_audit.py (async, best-effort)
```

### 3. Chat Pipeline (Streaming)

```
Usuario pregunta
       ↓
  stream_answer_query.py
       ↓ (embed → retrieve → build context)
  LLM genera tokens...
       ↓
  yield StreamChunk(type="token", content="...")
  yield StreamChunk(type="token", content="...")
  ...
  yield StreamChunk(type="sources", sources=[...])
  yield StreamChunk(type="done", confidence=score)
```

## Principios

1. **Un Use Case = Una Acción:** Cada archivo hace UNA cosa bien. No hay monstruos de 500 líneas.
2. **Orquestación, no Implementación:** Los use cases llaman a servicios/repos, no hacen SQL ni HTTP directamente.
3. **DTOs Explícitos:** Inputs y Results tipados con dataclasses.
4. **Fail-Fast:** Validaciones al inicio del use case (workspace existe, usuario tiene permiso).
5. **Best-Effort Audit:** La auditoría nunca bloquea el flujo principal.

## Cómo agregar un nuevo Use Case

1. Decide a qué feature pertenece (chat, ingestion, documents, workspace).
2. Crea el archivo `{verbo}_{sustantivo}.py` en esa carpeta.
3. Define `{UseCase}Input` y `{UseCase}Result` dataclasses.
4. Exporta en el `__init__.py` de la subcarpeta.
5. Añádelo al `__all__`.
6. Documenta en este README.

---

**Nota:** Los use cases dependen de los helpers de `application/` (como `context_builder`, `rate_limiting`) y de los puertos del `domain/` (repositorios, servicios). Nunca importan directamente de `infrastructure/`.
