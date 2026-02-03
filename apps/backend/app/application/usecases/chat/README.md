# chat
Como un **motor de conversación**: retrieval + generación + historial.

## 🎯 Misión
Este paquete implementa los casos de uso de chat/RAG: búsqueda semántica, respuesta con LLM, streaming y gestión de conversaciones.

### Qué SÍ hace
- Ejecuta retrieval semántico (similaridad o MMR) dentro de un workspace.
- Orquesta generación de respuestas con LLM usando contexto construido.
- Maneja historial de conversación (crear, listar, limpiar).
- Registra feedback y auditoría de respuestas.

### Qué NO hace (y por qué)
- No implementa HTTP ni parsing de requests. Razón: eso vive en `interfaces/`. Consecuencia: los use cases son invocables desde HTTP o worker.
- No toca SQL ni SDKs externos directamente. Razón: el IO está en `infrastructure/`. Consecuencia: depende de puertos del dominio.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `README.md` | Documento | Guía del bounded context Chat. |
| `__init__.py` | Archivo Python | Exports públicos (Inputs/UseCases). |
| `answer_query.py` | Archivo Python | RAG completo: embed → retrieve → contexto → LLM. |
| `answer_query_with_history.py` | Archivo Python | RAG multi-turn con historial persistente. |
| `chat_utils.py` | Archivo Python | Helpers de formato de historial. |
| `clear_conversation.py` | Archivo Python | Limpia mensajes de una conversación. |
| `create_conversation.py` | Archivo Python | Crea conversación y devuelve ID. |
| `get_conversation_history.py` | Archivo Python | Devuelve historial persistido. |
| `record_answer_audit.py` | Archivo Python | Auditoría best-effort de respuestas. |
| `search_chunks.py` | Archivo Python | Retrieval sin LLM (solo búsqueda). |
| `stream_answer_query.py` | Archivo Python | RAG con streaming SSE. |
| `vote_answer.py` | Archivo Python | Feedback/votos por respuesta. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output.

- **Retrieval (SearchChunks)**
- Requiere `workspace_id` y `query`.
- Genera embedding, busca chunks y aplica filtro de prompt injection.
- `top_k` se sanitiza con límites defensivos (ver código).
- **Respuesta (AnswerQuery)**
- Resuelve acceso al workspace.
- Recupera chunks, aplica rerank si está habilitado.
- Construye contexto con `ContextBuilder` y llama al LLM.
- **Historial (AnswerQueryWithHistory)**
- Resuelve/crea conversación, carga historial.
- Reescribe query si aplica y persiste mensajes best-effort.
- **Streaming**
- Emite eventos SSE (`sources`, `token`, `done`, `error`).
- No reintenta durante iteración del stream.

## 🔗 Conexiones y roles
- **Rol arquitectónico:** Application (use cases RAG).
- **Recibe órdenes de:** routers HTTP (query/chat) y worker.
- **Llama a:** `EmbeddingService`, `LLMService`, `DocumentRepository`, repos de conversación/feedback/auditoría.
- **Reglas de límites:** sin HTTP ni SQL directo; errores tipados `DocumentError`.

## 👩‍💻 Guía de uso (Snippets)
```python
# Por qué: muestra el contrato mínimo del módulo.
from app.container import get_search_chunks_use_case
from app.application.usecases.chat.search_chunks import SearchChunksInput

use_case = get_search_chunks_use_case()
result = use_case.execute(SearchChunksInput(query="q", workspace_id="...", actor=None))
```

```python
# Por qué: ejemplo de integración sin infraestructura real.
from app.container import get_answer_query_use_case
from app.application.usecases.chat.answer_query import AnswerQueryInput

use_case = get_answer_query_use_case()
result = use_case.execute(AnswerQueryInput(query="q", workspace_id="...", actor=None))
```

```python
# Por qué: deja visible el flujo principal.
from app.container import get_answer_query_with_history_use_case
from app.application.usecases.chat.answer_query_with_history import AnswerQueryWithHistoryInput

use_case = get_answer_query_with_history_use_case()
use_case.execute(AnswerQueryWithHistoryInput(query="q", workspace_id="...", conversation_id=None, actor=None))
```

## 🧩 Cómo extender sin romper nada
- Si agregás un use case, mantené Input/Result tipados y `execute()`.
- Usá `workspace_access` para validar acceso antes de retrieval/LLM.
- Si necesitás IO nuevo, definí puerto en `domain/` y adapter en `infrastructure/`.
- Cableá en `app/container.py`.
- Tests: unit en `apps/backend/tests/unit/application/`, integration en `apps/backend/tests/integration/`.

## 🆘 Troubleshooting
- **Síntoma:** `FORBIDDEN` al chatear.
- **Causa probable:** actor sin acceso al workspace.
- **Dónde mirar:** `workspace_access.py`.
- **Solución:** construir actor válido o ajustar ACL.
- **Síntoma:** retrieval devuelve vacío.
- **Causa probable:** embeddings deshabilitados o `top_k` bajo.
- **Dónde mirar:** `search_chunks.py` y container.
- **Solución:** revisar provider y límites.
- **Síntoma:** streaming falla a mitad.
- **Causa probable:** excepción durante el stream.
- **Dónde mirar:** `stream_answer_query.py` y `crosscutting/streaming.py`.
- **Solución:** manejar error y revisar logs.
- **Síntoma:** no se guarda historial.
- **Causa probable:** repo de conversación no configurado.
- **Dónde mirar:** `container.py`.
- **Solución:** cablear repository o usar in-memory.

## 🔎 Ver también
- `../README.md`
- `../documents/document_results.py`
- `../workspace/workspace_access.py`
- `../../../interfaces/api/http/routers/query.py`
