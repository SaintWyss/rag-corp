# Use Cases: Chat / RAG

## 🎯 Misión
Implementar los casos de uso de chat y RAG: búsqueda semántica, generación de respuestas, streaming y manejo de conversación.

**Qué SÍ hace**
- Ejecuta retrieval (SearchChunks) y generación (AnswerQuery).
- Orquesta conversación con historial persistente.
- Provee streaming de tokens para la UI.

**Qué NO hace**
- No define endpoints HTTP ni schemas (eso vive en interfaces).
- No implementa DB/LLM concretos (usa puertos del dominio).

**Analogía (opcional)**
- Es el “motor de preguntas y respuestas” del backend.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | Exports de los casos de uso de chat. |
| 🐍 `answer_query.py` | Archivo Python | RAG completo: embed → retrieve → contexto → LLM. |
| 🐍 `answer_query_with_history.py` | Archivo Python | RAG con historial conversacional persistido. |
| 🐍 `chat_utils.py` | Archivo Python | Helpers de formato de historial para prompts. |
| 🐍 `clear_conversation.py` | Archivo Python | Limpieza de conversaciones. |
| 🐍 `create_conversation.py` | Archivo Python | Creación de conversaciones nuevas. |
| 🐍 `get_conversation_history.py` | Archivo Python | Lectura de historial de conversación. |
| 📄 `README.md` | Documento | Esta documentación. |
| 🐍 `record_answer_audit.py` | Archivo Python | Registro de auditoría de respuestas. |
| 🐍 `search_chunks.py` | Archivo Python | Retrieval semántico sin generación. |
| 🐍 `stream_answer_query.py` | Archivo Python | RAG con streaming de tokens. |
| 🐍 `vote_answer.py` | Archivo Python | Votos/feedback sobre respuestas. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output (flujo típico de RAG):
- **Input**: `AnswerQueryInput` / `SearchChunksInput` con `workspace_id`, `query` y `actor`.
- **Proceso**: policy de acceso → embeddings → retrieval (similarity/MMR) → filtro de inyección → context builder → LLM.
- **Output**: `AnswerQueryResult` o `SearchChunksResult` con error tipado si aplica.

Tecnologías/librerías usadas aquí:
- dataclasses/typing; servicios externos se consumen vía puertos.

Flujo típico:
- `SearchChunksUseCase.execute()` retorna matches (sin LLM).
- `AnswerQueryUseCase.execute()` retorna `QueryResult` con fuentes.
- `StreamAnswerQueryUseCase.execute()` retorna stream de `StreamChunk`.

## 🔗 Conexiones y roles
- Rol arquitectónico: Application (Use Cases).
- Recibe órdenes de: Interfaces HTTP (`routers/query.py`).
- Llama a: repositorios de documentos/workspaces, EmbeddingService, LLMService.
- Contratos y límites: no conoce FastAPI ni SQL; usa puertos del dominio.

## 👩‍💻 Guía de uso (Snippets)
```python
from uuid import uuid4
from app.application.usecases.chat.answer_query import AnswerQueryInput
from app.container import get_answer_query_use_case

use_case = get_answer_query_use_case()
result = use_case.execute(
    AnswerQueryInput(query="¿Qué dice el contrato?", workspace_id=uuid4(), actor=None)
)
```

## 🧩 Cómo extender sin romper nada
- Agrega un nuevo caso de uso como módulo (p. ej. `summarize_conversation.py`).
- Define su `*Input`/`*Result` y errores tipados en `document_results.py` si aplica.
- Usa `resolve_workspace_for_read/write` para acceso consistente.
- Exporta el caso de uso en `chat/__init__.py` si es público.
- Cablea en `app/container.py` y crea tests unitarios.

## 🆘 Troubleshooting
- Síntoma: `FORBIDDEN` en queries → Causa probable: actor/policy → Mirar `workspace_access.py`.
- Síntoma: respuestas vacías → Causa probable: `top_k` inválido o sin chunks → Mirar `search_chunks.py`.
- Síntoma: streaming no emite tokens → Causa probable: LLM no soporta stream → Mirar `stream_answer_query.py`.

## 🔎 Ver también
- [Use cases](../README.md)
- [Documents results](../documents/document_results.py)
- [Interfaces query router](../../../interfaces/api/http/routers/query.py)
