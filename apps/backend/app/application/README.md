# Application Layer (Core Logic)

Esta capa contiene la lógica de coordinación de la aplicación, actuando como intermediario entre la Infraestructura (detalles técnicos) y el Dominio (reglas de negocio puras).

## Estructura

```
application/
├── usecases/                   # Casos de uso (Entry points de negocio)
│   ├── chat/                   # RAG + Chat conversacional
│   ├── documents/              # Resultados y tipos compartidos
│   ├── ingestion/              # Carga y procesamiento de documentos
│   └── workspace/              # Gestión de workspaces
├── context_builder.py          # Ensamblador de contexto para RAG
├── prompt_injection_detector.py # Políticas de seguridad
├── rate_limiting.py            # Control de cuotas y rate limiting
├── dev_seed_admin.py           # Tarea: Seed de usuario Admin
├── dev_seed_demo.py            # Tarea: Seed de entorno Demo
└── __init__.py                 # Exports públicos
```

## Componentes Compartidos (Shared Logic)

Estos módulos son utilizados por múltiples casos de uso para evitar duplicación de lógica compleja.

### 1. `context_builder.py` (The Grounding Assembler)

Es el responsable de armar el contexto que se envía al LLM.

- **Responsabilidad:** Toma una lista de chunks y los formatea con delimitadores de seguridad.
- **Seguridad:** Aplica sanitización (escapa `---[S#]---` en el contenido) para evitar confusión del modelo.
- **Presupuesto:** Implementa un algoritmo de "mochila" (Knapsack) para llenar el contexto hasta `max_size` sin cortar chunks por la mitad.
- **Grounding:** Genera la sección "FUENTES" alineada con las citas `[S#]` del texto.
- **Future-proofing:** Acepta un `size_counter` inyectable para integrar tiktoken (tokens reales) cuando se necesite.

### 2. `prompt_injection_detector.py` (The Security Guard)

Sistema de defensa en profundidad.

- **Responsabilidad:** Analiza texto no confiable (chunks recuperados) buscando patrones de ataque.
- **Estrategia:** No borra datos, pero marca el contenido o lo mueve al final (`downrank`).
- **Patrón:** Rule Engine data-driven (Reglas Regex con pesos).

### 3. `rate_limiting.py` (Usage Control) 🆕

Sistema de control de cuotas para prevenir abuso y gestionar costos.

- **Responsabilidad:** Verificar y registrar uso de recursos (mensajes, tokens, uploads).
- **Estrategia:** Sliding Window Counter con ventanas de tiempo configurables.
- **Implementaciones:** `InMemoryQuotaStorage` (dev/testing), fácil de extender a Redis/Postgres.
- **Uso típico:**
  ```python
  limiter = RateLimiter(storage, config)
  result = limiter.check("messages", user_id=user_id)
  if not result.allowed:
      raise RateLimitExceeded(result.retry_after_seconds)
  ```

### 4. `query_rewriter.py` (RAG Enhancement) 🆕

Mejora la precisión del RAG reescribiendo queries ambiguos o incompletos.

- **Responsabilidad:** Detectar queries que necesitan contexto y reescribirlos.
- **Problema que resuelve:** "¿y eso?" → "¿La política de vacaciones aplica a part-time?"
- **Estrategia:** Analiza patrones (pronombres, palabras de seguimiento) + usa LLM si necesario.
- **Uso típico:**
  ```python
  rewriter = QueryRewriter(llm_service, enabled=True)
  result = rewriter.rewrite(query, history)
  search_query = result.rewritten_query  # Usar para retrieval
  # result.was_rewritten = True/False
  # result.reason = "context_expanded" / "query_already_clear"
  ```

### 5. `reranker.py` (RAG Enhancement) 🆕

Reordena chunks recuperados por relevancia semántica real.

- **Responsabilidad:** Mejorar la selección de chunks después del retrieval vectorial.
- **Problema que resuelve:** Cosine similarity es rápido pero "shallow". El reranker evalúa relevancia real.
- **Estrategia:** Recuperar 20 chunks → Rerankar → Quedarse con los mejores 5.
- **Modos disponibles:**
  - `DISABLED`: Sin reranking (orden original).
  - `HEURISTIC`: Reglas simples (keyword overlap, longitud). Rápido.
  - `LLM`: Usa el LLM para puntuar cada chunk. Más preciso pero más lento.
- **Uso típico:**
  ```python
  reranker = ChunkReranker(llm_service, mode=RerankerMode.HEURISTIC)
  result = reranker.rerank(query, chunks, top_k=5)
  best_chunks = result.chunks
  # result.scores = [8.5, 7.2, 6.8, ...]  # Si aplica
  ```

## Casos de Uso (Use Cases)

Los casos de uso están organizados por feature en `usecases/`:

### Chat (`usecases/chat/`)

| Use Case                        | Descripción                                                |
| ------------------------------- | ---------------------------------------------------------- |
| `AnswerQueryUseCase`            | RAG puro (stateless): embedding → retrieval → LLM          |
| `StreamAnswerQueryUseCase` 🆕   | RAG con streaming de tokens (efecto "máquina de escribir") |
| `AnswerQueryWithHistoryUseCase` | RAG + contexto conversacional + persistencia               |
| `SearchChunksUseCase`           | Solo retrieval (sin LLM) para debugging/UI                 |
| `CreateConversationUseCase`     | Inicia una nueva sesión de chat                            |
| `GetConversationHistoryUseCase` | Recupera mensajes de una conversación                      |
| `ClearConversationUseCase`      | Limpia el historial de una conversación                    |
| `VoteAnswerUseCase` 🆕          | Feedback del usuario (RLHF - 👍/👎)                        |

**Utilities:** `chat_utils.py` contiene helpers para formatear historial (`format_conversation_for_prompt`).

**Streaming Protocol:**

```python
for chunk in stream_use_case.execute(input_data):
    if chunk.type == "token":
        print(chunk.content, end="")  # Token de texto
    elif chunk.type == "sources":
        render_sources(chunk.sources)  # Fuentes estructuradas
    elif chunk.type == "done":
        show_confidence(chunk.confidence)  # Score de confianza
```

### Ingestion (`usecases/ingestion/`)

| Use Case                          | Descripción                                 |
| --------------------------------- | ------------------------------------------- |
| `UploadDocumentUseCase`           | Sube y persiste un documento (con rollback) |
| `GetDocumentStatusUseCase`        | Consulta el estado de procesamiento         |
| `CancelDocumentProcessingUseCase` | Cancela documentos atascados                |

### Workspace (`usecases/workspace/`)

| Use Case                 | Descripción                         |
| ------------------------ | ----------------------------------- |
| `ListDocumentsUseCase`   | Lista documentos de un workspace    |
| `DeleteDocumentsUseCase` | Elimina documentos con autorización |

## Value Objects del Dominio 🆕

El módulo `domain/value_objects.py` contiene objetos de valor inmutables con enfoque empresarial:

### SourceReference (Fuentes Estructuradas)

```python
# Permite al frontend renderizar "chips" clickeables con info de cada fuente
source = SourceReference(
    index=1,
    document_title="Manual de RRHH",
    snippet="La política de vacaciones...",
    relevance_score=0.85,
)
```

### ConfidenceScore (Score de Confianza - Enfoque Empresarial)

```python
# Indica al usuario si debe verificar la respuesta
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

### AnswerAuditRecord (Trazabilidad / Compliance)

```python
# Registro de auditoría para cada respuesta (compliance empresarial)
audit = AnswerAuditRecord(
    record_id="audit-001",
    timestamp=datetime.now(UTC).isoformat(),
    user_id=user_id,
    workspace_id=workspace_id,
    query="¿Cuál es la política de vacaciones?",
    answer_preview="La política establece...",
    confidence_level="high",
    confidence_value=0.85,
    requires_verification=False,
    sources_count=3,
)
# audit.is_high_risk = False
# audit.audit_summary = "[timestamp] User=email Query='...' Confidence=high Sources=3"
```

### UsageQuota (Rate Limiting)

```python
quota = UsageQuota(limit=100, used=45, resource="messages")
# quota.remaining = 55
# quota.is_exceeded = False
# quota.usage_percentage = 45.0
```

## Tareas de Inicialización (Seed Tasks)

Estos scripts se ejecutan al inicio (`main.py`) para preparar el entorno:

- **`dev_seed_admin.py`:** Asegura que exista un super-admin (local + E2E).
- **`dev_seed_demo.py`:** Crea un entorno completo para demos locales.

## Principios de la Capa

1. **Orquestación, no Cálculo:** Conecta componentes sin hacer cálculos complejos.
2. **Fail-Fast:** Configuraciones inválidas lanzan excepciones inmediatas.
3. **Observabilidad:** Logs estructurados y métricas de tiempo.
4. **Inyección de Dependencias:** Cada use case recibe dependencias vía constructor.
5. **Contratos Explícitos:** Inputs/Outputs tipados con dataclasses.
6. **Enfoque Empresarial:** Trazabilidad, compliance y seguridad integrados.
