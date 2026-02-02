# Feature: Chat & RAG

## 🎯 Misión

Contiene toda la lógica para la **Experiencia Conversacional Inteligente**.
Aquí vive el algoritmo RAG (Retrieval-Augmented Generation), el manejo de historial de chat y el feedback de usuarios.

**Qué SÍ hace:**

- Implementa el flujo RAG: Pregunta -> Embedding -> Búsqueda -> Prompt -> LLM.
- Maneja streaming de respuestas (Token a Token).
- Gestiona sesiones de chat (Crear, Listar, Borrar).
- Registra votos/feedback de usuarios.

**Analogía:**
Es el Bibliotecario experto que no solo busca el libro, sino que lo lee y te resume la respuesta a tu pregunta.

## 🗺️ Mapa del territorio

| Recurso                        | Tipo       | Responsabilidad (en humano)                                             |
| :----------------------------- | :--------- | :---------------------------------------------------------------------- |
| `answer_query.py`              | 🐍 Archivo | **RAG Estándar**. Respuesta completa de una sola vez (stateless).       |
| `answer_query_with_history.py` | 🐍 Archivo | **Chat RAG**. Respuesta considerando mensajes anteriores.               |
| `chat_utils.py`                | 🐍 Archivo | Helpers para formatear mensajes del historial para el LLM.              |
| `clear_conversation.py`        | 🐍 Archivo | Borra mensajes de una sesión.                                           |
| `create_conversation.py`       | 🐍 Archivo | Inicia una nueva sesión de chat vacía.                                  |
| `get_conversation_history.py`  | 🐍 Archivo | Recupera los mensajes previos de una sesión.                            |
| `record_answer_audit.py`       | 🐍 Archivo | Guarda trazas de auditoría de respuestas generadas.                     |
| `search_chunks.py`             | 🐍 Archivo | **Retrieval Only**. Solo busca fragmentos relevantes sin llamar al LLM. |
| `stream_answer_query.py`       | 🐍 Archivo | **Streaming RAG**. Generador que emite tokens en tiempo real.           |
| `vote_answer.py`               | 🐍 Archivo | Registra si una respuesta fue útil (👍/👎).                             |

## ⚙️ ¿Cómo funciona por dentro?

### Flujo RAG (`answer_query.py`)

1.  **Rewrite:** Reescribe la pregunta si es ambigua.
2.  **Embed:** Convierte la pregunta a vector.
3.  **Retrieve:** Busca chunks similares en `DocumentRepository`.
4.  **Rerank:** Reordena los chunks por relevancia.
5.  **Generate:** Construye prompt con `ContextBuilder` e invoca al `LLMService`.

### Streaming

Usa generadores de Python (`yield`) para pasar los tokens desde el LLM hasta la API a medida que se generan.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Use Cases (Chat Feature).
- **Colabora con:** `LLMService`, `EmbeddingService`, `DocumentRepository`.

## 👩‍💻 Guía de uso (Snippets)

### Ejecutar una búsqueda simple (SearchChunks)

```python
use_case = SearchChunksUseCase(document_repo, embedding_service)
results = use_case.execute(
    SearchChunksInput(query="política de gastos", workspace_id=ws_id)
)
for chunk in results.chunks:
    print(chunk.content)
```

## 🧩 Cómo extender sin romper nada

1.  **Nuevos Modelos:** Si quieres soportar "Thinking Models", modifica `answer_query.py` o crea un `think_answer_query.py`.
2.  **Historial:** La gestión de memoria está en `chat_utils.py`.

## 🆘 Troubleshooting

- **Síntoma:** Respuestas lentas.
  - **Causa:** El modelo LLM es muy grande o el Reranker está tardando.
- **Síntoma:** "I don't know".
  - **Causa:** El retrieval no trajo chunks relevantes (revisar embeddings).

## 🔎 Ver también

- [Use Case Hub](../README.md)
