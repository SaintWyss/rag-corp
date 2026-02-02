# Use Cases: Chat / RAG

Analogía breve: este paquete es el **motor de conversación**. Toma una pregunta, busca evidencia en documentos (retrieval) y genera una respuesta; además mantiene el hilo (historial) y registra feedback (votos/auditoría).

## 🎯 Misión

Este directorio implementa los **casos de uso de Chat** del backend: el pipeline RAG (retrieval + generación), la gestión de conversaciones persistentes (crear, leer historial, limpiar) y el circuito de calidad (auditoría best‑effort y votos tipo RLHF).

Si abrís esta carpeta, deberías salir con tres ideas claras:

* **Qué operaciones ofrece el backend para “chatear”** (y qué devuelve cada una).
* **Cómo es el flujo técnico del RAG** (embeddings → búsqueda → post‑proceso → prompt → LLM).
* **Qué puertos necesita** (repositorios/servicios) y qué límites respeta (sin HTTP, sin SQL directo).

Ruta rápida (para orientarte en 30 segundos):

* **Solo búsqueda (sin LLM):** `search_chunks.py`
* **RAG completo (respuesta final):** `answer_query.py`
* **RAG + historial persistente (multi‑turn):** `answer_query_with_history.py`
* **RAG con streaming (tokens):** `stream_answer_query.py`
* **Conversaciones (CRUD mínimo):** `create_conversation.py`, `get_conversation_history.py`, `clear_conversation.py`
* **Calidad / feedback:** `vote_answer.py`, `record_answer_audit.py`

**Qué SÍ hace**

* Define DTOs de entrada/salida (`*Input`, `*Result`) y errores tipados (`DocumentError`).
* Orquesta el pipeline RAG sin conocer HTTP:

  * Calcula embeddings.
  * Recupera chunks relevantes del repositorio.
  * Aplica filtros defensivos (prompt injection) y re‑ranking.
  * Construye contexto y genera la respuesta con el LLM.
* Mantiene historial conversacional persistido (append/get/clear) vía `ConversationRepository`.
* Permite feedback del usuario (votos) con idempotencia (un voto por mensaje por usuario).

**Qué NO hace (y por qué)**

* No define endpoints ni validación de request HTTP.

  * **Por qué:** los casos de uso son consumibles tanto por HTTP como por worker; la validación de protocolo (headers, query params) vive en `interfaces/`.
* No implementa DB/Redis/LLM concretos.

  * **Por qué:** depende de **puertos** (Protocols/Interfaces). Las implementaciones están en `infrastructure/` y se conectan vía `container.py`.

---

## 🗺️ Mapa del territorio

| Recurso                        | Tipo         | Responsabilidad (en humano)                                                                                           |
| :----------------------------- | :----------- | :-------------------------------------------------------------------------------------------------------------------- |
| `__init__.py`                  | 🐍 Archivo   | Exporta el API público del paquete (casos de uso y DTOs relevantes).                                                  |
| `answer_query.py`              | 🐍 Archivo   | RAG “clásico”: embed → retrieve → (filtro/rerank) → contexto → LLM → resultado final.                                 |
| `answer_query_with_history.py` | 🐍 Archivo   | RAG multi‑turn: carga historial, reescribe la query si hace falta, persiste mensajes y delega a `AnswerQueryUseCase`. |
| `search_chunks.py`             | 🐍 Archivo   | Retrieval sin generación: devuelve los chunks candidatos y metadata de selección/rerank.                              |
| `stream_answer_query.py`       | 🐍 Archivo   | Variante de RAG que emite eventos de streaming (`START`/`TOKEN`/`END`/`ERROR`) para UIs en tiempo real.               |
| `chat_utils.py`                | 🐍 Archivo   | Formatea historial para prompts (estructura compacta y segura).                                                       |
| `create_conversation.py`       | 🐍 Archivo   | Crea una conversación y devuelve un `conversation_id` estable.                                                        |
| `get_conversation_history.py`  | 🐍 Archivo   | Devuelve mensajes persistidos (con límites/orden) para mostrar o para rewriter.                                       |
| `clear_conversation.py`        | 🐍 Archivo   | Limpia mensajes de una conversación (reset del hilo).                                                                 |
| `record_answer_audit.py`       | 🐍 Archivo   | Registra auditoría de respuestas (best‑effort) para trazabilidad/cumplimiento.                                        |
| `vote_answer.py`               | 🐍 Archivo   | Registra voto del usuario sobre un mensaje (👍/👎/neutral), con idempotencia y metadata.                              |
| `README.md`                    | 📄 Documento | Esta documentación.                                                                                                   |

Operaciones de negocio (vista “menú”):

* **Retrieval:** `SearchChunksUseCase.execute(SearchChunksInput) -> SearchChunksResult`
* **Respuesta final:** `AnswerQueryUseCase.execute(AnswerQueryInput) -> AnswerQueryResult`
* **Respuesta con historial:** `AnswerQueryWithHistoryUseCase.execute(AnswerQueryWithHistoryInput) -> AnswerQueryWithHistoryResult`
* **Streaming:** `StreamAnswerQueryUseCase.execute(StreamAnswerQueryInput) -> Iterator[StreamChunk]`
* **Conversaciones:** `CreateConversationUseCase`, `GetConversationHistoryUseCase`, `ClearConversationUseCase`
* **Feedback/auditoría:** `VoteAnswerUseCase`, `RecordAnswerAuditUseCase`

---

## ⚙️ ¿Cómo funciona por dentro?

### Conceptos mínimos que aparecen en este paquete

* **RAG (Retrieval‑Augmented Generation):** primero recuperás evidencia (chunks) de documentos; después le pedís al LLM que responda usando esa evidencia.
* **Embedding:** vector numérico que representa el significado de una frase/documento. Sirve para comparar “similitud semántica”.
* **Chunk:** fragmento de documento (texto) que se indexa y se usa como evidencia. Vive como entidad del dominio (`Chunk`).
* **MMR (Maximal Marginal Relevance):** estrategia de selección que balancea relevancia y diversidad (evita traer 10 chunks casi iguales).

### Flujo real del RAG (AnswerQuery)

Pipeline típico dentro de `AnswerQueryUseCase`:

1. **Acceso al workspace (policy):** se resuelve acceso de lectura al `workspace_id` (bounded context Workspace). Si falla, se devuelve `DocumentError`.
2. **Sanitización de parámetros:** se normaliza `top_k` (y el número de candidatos) para evitar configuraciones peligrosas.
3. **Embeddings de la query:** se llama al puerto `EmbeddingService` con la query.
4. **Retrieval:** se consulta al puerto `ChunkRepository` (por similitud; opcionalmente MMR en algunos flows).
5. **Defensas antes del LLM:**

   * **Prompt injection filter:** `apply_injection_filter(...)` filtra chunks marcados en la ingesta (se apoya en metadata del chunk; no “adivina” en runtime).
   * **Reranking:** `ChunkReranker` puede reordenar candidatos (heurístico o con un scorer) y dejar trazabilidad en `metadata`.
6. **Construcción de contexto:** `ContextBuilder` arma el bloque de evidencia dentro de un límite (caracteres/tokens aproximados).
7. **Generación:** se llama al puerto `LLMService` para producir la respuesta.
8. **Salida tipada:** se retorna `AnswerQueryResult` con:

   * respuesta (texto),
   * chunks utilizados (evidencia),
   * `metadata` (timings, rerank info, sanitización).

### Retrieval sin generación (SearchChunks)

`SearchChunksUseCase` aplica el mismo “lado izquierdo” del pipeline:

* embed de la query → búsqueda de candidatos → (filtro/rerank) → devuelve **matches**.

Este caso de uso es útil cuando:

* querés debuggear retrieval sin pagar LLM,
* necesitás que la UI muestre fuentes antes de generar,
* querés medir calidad de búsqueda.

### Multi‑turn (AnswerQueryWithHistory)

`AnswerQueryWithHistoryUseCase` agrega estado:

1. Valida acceso al workspace.
2. Resuelve `conversation_id` (si no existe, crea una conversación nueva).
3. Lee historial (limitado) con `ConversationRepository.get_messages(...)`.
4. **Reescribe la query** con `QueryRewriter` cuando detecta preguntas “dependientes del contexto” (por ejemplo, pronombres o queries muy cortas).
5. Llama internamente a `AnswerQueryUseCase` con la query original o reescrita.
6. Persiste los mensajes (usuario/asistente) **best‑effort**: si falla la persistencia del historial, no rompe el flujo principal.
7. Devuelve `AnswerQueryWithHistoryResult` y agrega trazabilidad en `metadata`:

   * `_META_query_original`
   * `_META_query_rewritten`
   * `_META_rewrite_applied`

### Streaming (StreamAnswerQuery)

`StreamAnswerQueryUseCase` expone un contrato de streaming orientado a UI:

* Emite `StreamChunk` con tipos:

  * `START` (arranque + contexto mínimo)
  * `TOKEN` (tokens incrementales)
  * `END` (resultado final + métricas)
  * `ERROR` (error tipado)

Nota operativa importante (para no llevarte una sorpresa): en el estado actual del código, el módulo de streaming necesita alinearse con el helper de acceso a workspace (`workspace_access.resolve_workspace_for_read`) para recibir repositorios/ACL como el resto de casos de uso. Si activás streaming desde HTTP, validá este punto primero (ver Troubleshooting).

---

## 🔗 Conexiones y roles

* **Rol arquitectónico:** Application (Use Cases / Orquestación).
* **Recibe órdenes de:**

  * Interfaces HTTP (routers de query/chat).
  * Worker (jobs que necesiten ejecutar RAG fuera del request).
* **Llama a (puertos principales):**

  * `EmbeddingService` (vectorizar query).
  * `LLMService` (generación y, si aplica, streaming).
  * `ChunkRepository` (recuperación de chunks).
  * `WorkspaceRepository` + `WorkspaceAclRepository` (enforce de acceso a workspace).
  * `ConversationRepository` (historial persistente).
  * `FeedbackRepository` (votos).
  * `AnswerAuditRepository` (auditoría de respuestas).
* **Límites que respeta:**

  * no importa FastAPI/Starlette,
  * no arma SQL ni toca Redis directamente,
  * retorna resultados tipados para que la capa Interface mapee a HTTP (incluyendo RFC7807).

---

## 👩‍💻 Guía de uso (Snippets)

### A) Retrieval (sin LLM)

```python
from uuid import uuid4

from app.application.usecases.chat.search_chunks import SearchChunksInput
from app.container import get_search_chunks_use_case

use_case = get_search_chunks_use_case()
result = use_case.execute(
    SearchChunksInput(
        query="¿Qué dice el contrato sobre auditoría?",
        workspace_id=uuid4(),
        actor=None,
        top_k=8,
        use_mmr=True,
    )
)

if result.error:
    raise RuntimeError(result.error)

for match in result.matches:
    print(match.chunk_id, match.score)
```

### B) RAG “clásico” (respuesta final)

```python
from uuid import uuid4

from app.application.usecases.chat.answer_query import AnswerQueryInput
from app.container import get_answer_query_use_case

use_case = get_answer_query_use_case()
result = use_case.execute(
    AnswerQueryInput(
        query="Resumime el objetivo del backend.",
        workspace_id=uuid4(),
        actor=None,
        top_k=6,
    )
)

if result.error:
    raise RuntimeError(result.error)

print(result.answer)
```

### C) RAG con historial persistente (multi‑turn)

```python
from uuid import uuid4

from app.application.usecases.chat.answer_query_with_history import (
    AnswerQueryWithHistoryInput,
)
from app.container import get_answer_query_with_history_use_case

use_case = get_answer_query_with_history_use_case()
result = use_case.execute(
    AnswerQueryWithHistoryInput(
        query="¿Y eso cuánto cuesta?",
        workspace_id=uuid4(),
        conversation_id=None,  # crea una nueva si no hay
        actor=None,
    )
)

if result.error:
    raise RuntimeError(result.error)

print(result.answer)
print(result.metadata.get("_META_rewrite_applied"))
```

---

## 🧩 Cómo extender sin romper nada

1. **Nuevo caso de uso (nuevo archivo):**

   * Creá `mi_caso_de_uso.py` en este paquete.
   * Definí `MiCasoDeUsoInput` y `MiCasoDeUsoResult` (dataclasses, inmutables si aplica).

2. **Errores tipados:**

   * Reusá `DocumentError`/`DocumentErrorCode` para consistencia de mapeo a RFC7807.
   * Elegí `resource` y `message` que ayuden a debuggear sin filtrar secretos.

3. **Puertos primero, drivers después:**

   * Si necesitás IO nuevo, definí el puerto en `domain/repositories.py` o `domain/services.py`.
   * Implementá el adapter en `infrastructure/`.

4. **Cableado:**

   * Registrá factory/instancia en `app/container.py` (no instancies drivers dentro del use case).

5. **Export público:**

   * Si el caso de uso se consume desde fuera del paquete, agregalo a `chat/__init__.py`.

6. **Tests:**

   * Unit: mocks/fakes de puertos.
   * Integration: repos reales (Postgres/Redis) si aplica.

---

## 🆘 Troubleshooting

* **Síntoma:** `FORBIDDEN` al consultar o chatear

  * **Causa probable:** el `actor` no tiene acceso al workspace (ACL / modo PRIVATE/SHARED).
  * **Solución:** revisar `application/usecases/workspace/workspace_access.py` y el rol/permisos del actor.

* **Síntoma:** resultados de búsqueda vacíos aunque existan documentos

  * **Causa probable:** `top_k` muy bajo, embeddings deshabilitados o chunks sin index.
  * **Solución:** probar `SearchChunksUseCase` primero; verificar provider de embeddings en `container.py` y que exista ingesta.

* **Síntoma:** la respuesta ignora fuentes o “alucina”

  * **Causa probable:** contexto insuficiente (limitado por tamaño) o chunks irrelevantes.
  * **Solución:** revisar configuración del `ContextBuilder` (límite) y habilitar/ajustar `ChunkReranker`.

* **Síntoma:** streaming falla con error de argumentos / `TypeError` en acceso a workspace

  * **Causa probable:** el caso de uso de streaming no está alineado con la firma de `resolve_workspace_for_read` (necesita repos/ACL).
  * **Solución:** pasar `workspace_repository` y `acl_repository` como en los otros use cases, o refactorizar el check para usar el helper estándar.

* **Síntoma:** no se guarda historial pero la respuesta sale igual

  * **Causa probable:** persistencia best‑effort del historial falló (repo no disponible / adapter no configurado).
  * **Solución:** revisar implementación de `ConversationRepository` y logs del backend; el flujo principal no se corta por diseño.

---

## 🔎 Ver también

* [Use Cases (hub)](../README.md)
* [Documents (errores/resultados)](../documents/document_results.py)
* [Workspace access helper](../workspace/workspace_access.py)
* [Interfaces query router](../../../interfaces/api/http/routers/query.py)
* [Application services (rewriter/reranker/injection)](../../README.md)
