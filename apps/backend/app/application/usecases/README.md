# Use Cases (casos de uso)

Analogía breve: este directorio es el **catálogo de operaciones** del backend. Cada caso de uso es una “acción completa” (con principio y fin) que alguien puede ejecutar: desde HTTP, desde un job del worker o desde un test.

## 🎯 Misión

Este paquete organiza y expone los **casos de uso** del sistema por bounded context (DDD): `chat/`, `documents/`, `ingestion/` y `workspace/`. Un caso de uso representa una unidad de comportamiento de aplicación: valida precondiciones, aplica políticas (acceso, límites, seguridad) y coordina **puertos del dominio** (repos/servicios) para producir un resultado tipado.

Si estás entrando por primera vez, este README te deja claro:

* **Qué operaciones existen** y dónde están.
* **Cómo se llaman** (contrato `Input → UseCase.execute() → Result`).
* **Qué podés importar como API pública** (barrel exports de `usecases/__init__.py`).

### Índice por área (qué vas a encontrar en cada subpaquete)

* **Chat (`chat/`)** — RAG, búsqueda semántica, streaming y conversación.

  * `answer_query.py` → RAG completo (retrieval + generación)
  * `stream_answer_query.py` → RAG con streaming de tokens
  * `search_chunks.py` → retrieval puro (sin LLM)
  * `answer_query_with_history.py` → RAG + contexto conversacional
  * `create_conversation.py`, `get_conversation_history.py`, `clear_conversation.py` → ciclo de vida de conversación
  * `vote_answer.py` → feedback (RLHF-like)
  * `record_answer_audit.py` → auditoría best-effort

* **Documents (`documents/`)** — CRUD de documentos y resultados compartidos.

  * `list_documents.py`, `get_document.py`, `download_document.py`, `delete_document.py`, `update_document_metadata.py`
  * `document_results.py` → tipos compartidos de Result/Error para Document + RAG

* **Ingestion (`ingestion/`)** — subida, procesamiento, re-procesamiento y estado.

  * `upload_document.py` → persistir metadata + almacenar archivo + encolar procesamiento
  * `process_uploaded_document.py` → pipeline async (parse → chunk → embed → persist)
  * `ingest_document.py` → pipeline directo (validate → chunk → embed → persist)
  * `reprocess_document.py`, `cancel_document_processing.py`, `get_document_status.py`

* **Workspace (`workspace/`)** — gestión de workspaces + control de acceso.

  * `create_workspace.py`, `get_workspace.py`, `list_workspaces.py`, `update_workspace.py`
  * `share_workspace.py` (SHARED + ACL), `publish_workspace.py` (ORG_READ), `archive_workspace.py` (soft delete)
  * `workspace_access.py` → helpers para resolver acceso read/write (usado por documents/chat)
  * `workspace_results.py` → tipos compartidos de Result/Error para workspaces

**Qué SÍ hace**

* Define DTOs inmutables (`*Input` como `@dataclass(frozen=True)`) con defaults defensivos.
* Implementa `*UseCase` con un punto de entrada claro (normalmente `execute(...)`).
* Devuelve resultados **tipados** (`*Result`) con `error` tipado en lugar de filtrar excepciones.
* Centraliza contratos compartidos:

  * `documents/document_results.py` (errores y resultados para Document + RAG)
  * `workspace/workspace_results.py` (errores y resultados para Workspace)
* Publica una **API interna estable** (barrel exports) desde `usecases/__init__.py` para evitar imports frágiles.

**Qué NO hace (y por qué)**

* No implementa acceso directo a DB, Redis, S3, LLM SDKs.

  * **Por qué:** ese IO pertenece a `infrastructure/`; acá se habla con *puertos* (interfaces) y se inyectan implementaciones desde `app/container.py`.
* No expone endpoints HTTP ni parsea requests.

  * **Por qué:** la capa `interfaces/` es la que traduce HTTP → DTOs; los casos de uso deben poder ejecutarse igual desde worker/tests.
* No “adivina” validaciones de HTTP.

  * **Por qué:** aunque Interfaces haga validación de esquema, Application mantiene validaciones de **negocio/defensivas** (IDs requeridos, rangos, top_k máximo, etc.).

---

## 🗺️ Mapa del territorio

| Recurso          | Tipo         | Responsabilidad (en humano)                                                                       |
| :--------------- | :----------- | :------------------------------------------------------------------------------------------------ |
| 🐍 `__init__.py` | 🐍 Archivo   | API pública de la capa de use cases: re-exporta Inputs/UseCases/Results y evita imports frágiles. |
| 📁 `chat/`       | 📁 Carpeta   | Use cases de RAG, búsqueda semántica y conversación (sync + streaming).                           |
| 📁 `documents/`  | 📁 Carpeta   | Use cases de documentos (CRUD) + modelos Result/Error compartidos.                                |
| 📁 `ingestion/`  | 📁 Carpeta   | Use cases de ingesta (upload → process → embed → persist) + control operativo.                    |
| 📁 `workspace/`  | 📁 Carpeta   | Use cases de workspaces + helpers de acceso + resultados/errores compartidos.                     |
| 📄 `README.md`   | 📄 Documento | Portada + mapa del paquete `usecases/` (este archivo).                                            |

---

## ⚙️ ¿Cómo funciona por dentro?

### 1) Contrato técnico común: `Input → execute() → Result`

Los casos de uso siguen un patrón consistente para que sea fácil:

* invocarlos desde HTTP o worker,
* testearlos sin emular transporte,
* y mapear errores de forma uniforme.

**Input (DTO)**

* Típicamente `@dataclass(frozen=True)`.
* Contiene únicamente lo necesario para la operación (query, workspace_id, actor, etc.).
* Defaults defensivos (por ejemplo `top_k` y límites máximos para evitar cargas excesivas).

**UseCase (orquestación)**

* Clase con dependencias explícitas por constructor.
* No crea repos ni clientes: los recibe inyectados (DIP).
* Aplica política de acceso (workspace read/write) y reglas fail-fast.

**Result (salida tipada)**

* `dataclass` con payload y `error`.
* Errores estables por código:

  * `DocumentErrorCode`: `VALIDATION_ERROR`, `FORBIDDEN`, `NOT_FOUND`, `CONFLICT`, `SERVICE_UNAVAILABLE`
  * `WorkspaceErrorCode`: `VALIDATION_ERROR`, `FORBIDDEN`, `NOT_FOUND`, `CONFLICT`

📌 Esta capa **prefiere resultados tipados** antes que excepciones porque:

* la UI/cliente puede decidir por `error.code` sin parsear mensajes,
* `interfaces/` puede mapear a RFC7807 sin “interpretar” stacktraces,
* tests pueden asertar comportamiento sin mocks de HTTP.

### 2) Bounded context (DDD): por qué existe esta estructura

El backend separa operaciones por “dominio funcional” (bounded context) para que:

* cada carpeta tenga un lenguaje consistente,
* las dependencias se mantengan acotadas,
* y sea difícil que un use case se vuelva un “god-module”.

Ejemplos concretos:

* `chat/` se enfoca en retrieval + generación (y sus políticas asociadas: rewriter/reranker/injection).
* `ingestion/` se enfoca en *pipeline* de datos (parsing, chunking, embeddings, persistencia).
* `documents/` y `workspace/` concentran CRUD y control de acceso/visibilidad.

### 3) Control de acceso de Workspace: un punto común para Document + RAG

Muchos flujos dependen de que un `workspace_id` sea **accesible**.
Para evitar duplicación, existe `workspace/workspace_access.py` que:

* carga el workspace,
* verifica estado (no archivado),
* resuelve ACL si aplica (visibilidad `SHARED`),
* y aplica la policy pura de `domain/workspace_policy.py`.

Detalle importante: `WorkspaceActor` **no es opcional** para flujos reales.

* Si `actor is None` o `actor.role is None` ⇒ forbidden por policy.

### 4) Composición de dependencias: `app/container.py`

Los UseCases no deciden implementaciones. `app/container.py` construye instancias:

* selecciona repositorios (Postgres vs in-memory),
* selecciona servicios (LLM real vs fake),
* aplica feature flags (rewriter/reranker, thresholds, top_k máximos).

Esto permite que:

* el mismo UseCase funcione en prod, dev, CI y tests,
* sin cambiar el código del caso de uso.

---

## 🔗 Conexiones y roles

* **Rol arquitectónico:** Application (Use Cases).

* **Recibe órdenes de:**

  * `interfaces/` (HTTP): routers crean `*Input` y llaman `execute()`.
  * `worker/` (RQ): jobs construyen inputs y ejecutan use cases (especialmente en ingesta/procesamiento).

* **Llama a:**

  * Dominio: entidades + puertos (`domain.repositories`, `domain.services`, policies).
  * Application helpers: `ContextBuilder`, `QueryRewriter`, `ChunkReranker`, `apply_injection_filter`, rate limiting, etc.
  * Infraestructura: **solo por inyección** (nunca por import directo).

* **Contratos y límites:**

  * Nada de FastAPI/Starlette acá.
  * Nada de SQL/SDKs acá.
  * Todo IO entra por dependencias tipadas.

---

## 👩‍💻 Guía de uso (Snippets)

> Estos ejemplos muestran cómo ejecutar casos de uso sin HTTP, usando el contenedor como composition root.

### 1) Retrieval puro (SearchChunks)

```python
from uuid import UUID

from app.application.usecases import SearchChunksInput
from app.container import get_search_chunks_use_case
from app.domain.workspace_policy import WorkspaceActor
from app.identity.users import UserRole

use_case = get_search_chunks_use_case()

actor = WorkspaceActor(user_id=UUID("00000000-0000-0000-0000-000000000001"), role=UserRole.ADMIN)

result = use_case.execute(
    SearchChunksInput(
        query="política de vacaciones",
        workspace_id=UUID("00000000-0000-0000-0000-000000000010"),
        actor=actor,
        top_k=5,
        use_mmr=True,
    )
)

if result.error:
    print(result.error.code, result.error.message)
else:
    print(len(result.matches), result.metadata)
```

### 2) Ingesta async (Upload → Process)

```python
from uuid import UUID

from app.application.usecases import UploadDocumentInput
from app.container import get_upload_document_use_case
from app.domain.workspace_policy import WorkspaceActor
from app.identity.users import UserRole

use_case = get_upload_document_use_case()
actor = WorkspaceActor(user_id=UUID("00000000-0000-0000-0000-000000000001"), role=UserRole.ADMIN)

result = use_case.execute(
    UploadDocumentInput(
        workspace_id=UUID("00000000-0000-0000-0000-000000000010"),
        actor=actor,
        filename="manual.pdf",
        content_type="application/pdf",
        # el archivo viaja como bytes/stream según el contrato del Input
    )
)

if result.error:
    print(result.error.code, result.error.message)
else:
    print("uploaded:", result.document_id)
```

> Nota: el procesamiento real suele ejecutarse como job (worker) llamando `ProcessUploadedDocumentUseCase`.

---

## 🧩 Cómo extender sin romper nada

### Checklist para agregar un use case nuevo

1. **Elegí el bounded context correcto** (`chat/`, `documents/`, `ingestion/`, `workspace/`).
2. **Nombrá el archivo** con verbo + sustantivo (`archive_workspace.py`, `rotate_api_key.py`).
3. Definí `@dataclass(frozen=True) <Name>Input` con:

   * campos mínimos,
   * defaults defensivos,
   * tipos precisos (UUID, enums, etc.).
4. Definí `<Name>UseCase` con constructor explícito:

   * repos/servicios como puertos,
   * settings/flags necesarios como parámetros (no globals).
5. Implementá `execute(input: <...Input>) -> <...Result>` con:

   * validación fail-fast (ids, rangos, límites),
   * policy de acceso (workspace read/write) si aplica,
   * llamadas a puertos del dominio,
   * error tipado (`DocumentError` / `WorkspaceError`).
6. **No hagas IO directo.** Si necesitás un capability nuevo:

   * agregá el puerto en `domain/`,
   * implementá el adapter en `infrastructure/`.
7. Cableá el caso de uso en `app/container.py` (factory `get_<...>_use_case`).
8. Exportá la API pública:

   * en el `__init__.py` del subpaquete,
   * y opcionalmente en `usecases/__init__.py` si se usa desde múltiples capas.
9. Agregá tests:

   * unit (sin IO) para invariantes y errores,
   * integration para DB/Redis/storage.

### Convenciones que conviene mantener

* Inputs inmutables (`frozen=True`) para evitar mutación accidental durante el flujo.
* Errores por código estable (no inventar códigos nuevos sin necesidad).
* `top_k` y tamaños siempre con máximos defensivos.
* Logging/metadata sin filtrar secretos (API keys, tokens, contenido privado).

---

## 🆘 Troubleshooting

* **Síntoma:** `ImportError` al importar desde `app.application.usecases`

  * **Causa probable:** falta export en `usecases/__init__.py` o en el `__init__.py` del subpaquete.
  * **Solución:** revisar `usecases/__init__.py` y el `__all__` (barrel exports).

* **Síntoma:** `FORBIDDEN` “inesperado”

  * **Causa probable:** `WorkspaceActor` es `None` o `actor.role` es `None`.
  * **Solución:** construir actor desde auth (`UserRole.ADMIN/EMPLOYEE`) y pasar `user_id`.

* **Síntoma:** `VALIDATION_ERROR` por `top_k`

  * **Causa probable:** excediste el máximo defensivo.
  * **Solución:** bajar `top_k` o revisar límites del use case (protección de performance).

* **Síntoma:** `SERVICE_UNAVAILABLE` en chat/ingestion

  * **Causa probable:** dependencia externa degradada (LLM/embeddings/storage).
  * **Solución:** revisar settings/credenciales y logs de infraestructura; el use case debería devolver error tipado, no reventar.

* **Síntoma:** `NOT_FOUND` aunque el id existe

  * **Causa probable:** workspace archivado o no accesible por policy/ACL.
  * **Solución:** revisar `workspace_access.py` (estado + ACL) y la visibility del workspace.

---

## 🔎 Ver también

* [Application layer](../README.md)
* [Chat](./chat/README.md)
* [Documents](./documents/README.md)
* [Ingestion](./ingestion/README.md)
* [Workspace](./workspace/README.md)
* [Composition root (`app/container.py`)](../../container.py)
