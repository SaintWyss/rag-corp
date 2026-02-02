# Application (casos de uso y servicios)

Analogía breve: esta carpeta es la **sala de mando** del backend. Acá se decide *qué* se hace (acciones de negocio) y *en qué orden*, pero no se habla HTTP ni se escribe SQL.

## 🎯 Misión

La capa **Application** orquesta el comportamiento del sistema en forma de **casos de uso** (acciones completas) y **servicios de aplicación** (políticas y utilidades reutilizables). Su responsabilidad es coordinar el Dominio y la Infraestructura a través de **puertos** (interfaces/Protocols) y devolver resultados **tipados** para que Interfaces (HTTP) y Worker (RQ) puedan transformarlos en respuestas o side-effects.

Si estás entrando por primera vez, este README es el índice para ubicar rápidamente “qué hace qué”:

* **Quiero ver las acciones de negocio (Use Cases)** → [`usecases/`](./usecases/README.md)

  * Chat/RAG → [`usecases/chat/`](./usecases/chat/README.md)
  * Documentos (CRUD) → [`usecases/documents/`](./usecases/documents/README.md)
  * Ingesta (pipeline async) → [`usecases/ingestion/`](./usecases/ingestion/README.md)
  * Workspaces (visibilidad/compartir) → [`usecases/workspace/`](./usecases/workspace/README.md)
* **Quiero entender cómo se arma el contexto RAG (con citas [S#] y FUENTES)** → [`context_builder.py`](./context_builder.py)
* **Quiero entender las políticas de seguridad contra prompt-injection** → [`prompt_injection_detector.py`](./prompt_injection_detector.py)
* **Quiero entender cómo se mejora el retrieval (rewriter + reranker)** → [`query_rewriter.py`](./query_rewriter.py) y [`reranker.py`](./reranker.py)
* **Quiero entender el rate limiting por cuota (messages/tokens/uploads)** → [`rate_limiting.py`](./rate_limiting.py)
* **Quiero entender seed de desarrollo (solo local / override E2E controlado)** → [`dev_seed_admin.py`](./dev_seed_admin.py) y [`dev_seed_demo.py`](./dev_seed_demo.py)

**Qué SÍ hace**

* Define **casos de uso** que representan acciones completas (ej: responder una pregunta, subir un documento, listar workspaces).
* Aplica **políticas** de producto/costo/seguridad (rate limiting, filtros de prompt-injection, límites de contexto).
* Modela **Inputs/Results** tipados para que las capas de entrada (HTTP/Worker) mapeen sin ambigüedad.
* Coordina puertos del dominio (repositorios/servicios) con implementaciones elegidas en el composition root (`app/container.py`).
* Contiene tareas de seed **con guardias estrictas** para no contaminar ambientes reales.

**Qué NO hace (y por qué)**

* No define endpoints HTTP ni parsing de requests.

  * **Por qué:** la Application debe ser invocable igual desde HTTP, desde un job, o desde tests; el protocolo de entrada vive en `interfaces/`.
* No ejecuta SQL ni toca drivers concretos (Postgres/Redis/S3/SDKs).

  * **Por qué:** esos detalles cambian con el entorno y se encapsulan en `infrastructure/`; acá solo se trabaja contra puertos.
* No decide “qué implementación usar” (prod vs test, fake vs real).

  * **Por qué:** esa decisión es de composición (DIP) y se centraliza en `app/container.py`.

---

## 🗺️ Mapa del territorio

| Recurso                           | Tipo         | Responsabilidad (en humano)                                                                                                                    |
| :-------------------------------- | :----------- | :--------------------------------------------------------------------------------------------------------------------------------------------- |
| 🐍 `__init__.py`                  | 🐍 Archivo   | API pública de la capa: re-exporta servicios de aplicación estables (ContextBuilder, RateLimiter, QueryRewriter, ChunkReranker, detector).     |
| 🐍 `context_builder.py`           | 🐍 Archivo   | **Assembler RAG**: arma el string de contexto con delimitadores `[S#]`, metadata trazable y sección `FUENTES`, con límite estricto por tamaño. |
| 🐍 `conversations.py`             | 🐍 Archivo   | Helpers de conversación: resolver/crear `conversation_id` y formatear historial en un texto consumible por LLM.                                |
| 🐍 `dev_seed_admin.py`            | 🐍 Archivo   | Seed de usuario admin para desarrollo con **guardia de seguridad** (solo local, salvo override E2E explícito).                                 |
| 🐍 `dev_seed_demo.py`             | 🐍 Archivo   | Seed demo local: crea usuarios demo y un workspace privado por usuario, de forma **idempotente**.                                              |
| 🐍 `prompt_injection_detector.py` | 🐍 Archivo   | Política de seguridad: detecta señales de prompt-injection y aplica filtro (`off/exclude/downrank`) usando metadata estable.                   |
| 🐍 `query_rewriter.py`            | 🐍 Archivo   | Servicio de mejora RAG: detecta queries ambiguas/cortas y usa un port LLM para reescritura contextual (con fallback seguro).                   |
| 🐍 `rate_limiting.py`             | 🐍 Archivo   | Rate limiting por cuota (messages/tokens/uploads) con ventana por hora, storage abstracto (port) y resultado tipado con `retry_after`.         |
| 🐍 `reranker.py`                  | 🐍 Archivo   | Reranking de chunks: `disabled/heuristic/llm` para reordenar por relevancia real y quedarte con `top_k`.                                       |
| 📁 `usecases/`                    | 📁 Carpeta   | Acciones completas del sistema agrupadas por feature (chat, documents, ingestion, workspace).                                                  |
| 📄 `README.md`                    | 📄 Documento | Portada + mapa general de la capa Application (este archivo).                                                                                  |

---

## ⚙️ ¿Cómo funciona por dentro?

### La regla central

**Application es orquestación.** En la práctica:

1. Recibe un **input** tipado (DTO/dataclass) desde Interfaces (HTTP) o desde Worker (job).
2. Valida reglas operativas (fail-fast) y aplica políticas (cuotas, límites, seguridad).
3. Invoca **puertos del dominio** (repositorios/servicios) para leer/escribir estado.
4. Devuelve un **resultado tipado** (Result/Output) que otra capa traduce a HTTP, logs, métricas o efectos.

### Servicios de Application (los “bloques reutilizables”)

Estos archivos existen porque hay comportamiento transversal que aparece en varios casos de uso:

* **ContextBuilder (`context_builder.py`)**

  * Arma el contexto que se inyecta al LLM para grounding.
  * Garantías técnicas importantes:

    * Delimitadores por chunk `---[S#]---` + cierre `---[FIN S#]---`.
    * Sección final `FUENTES:` alineada 1:1 con los índices `[S#]`.
    * Deduplicación **estable** (no reordena, preserva ranking).
    * Sanitiza colisiones con delimitadores y marca contenido sospechoso (best-effort).
    * Límite **estricto** por tamaño usando un contador inyectable (chars hoy, tokens mañana).

* **Prompt Injection Detector (`prompt_injection_detector.py`)**

  * Define un scoring determinista (`risk_score` ∈ [0,1]) + flags + slugs de patrones.
  * No guarda texto crudo: solo metadata estable.
  * `apply_injection_filter()` no “adivina”: actúa sobre `chunk.metadata` precomputada (idealmente en ingest/async).
  * Modos:

    * `off`: no cambia.
    * `exclude`: elimina chunks flaggeados.
    * `downrank`: mueve chunks riesgosos al final (estable, sin resortear por similitud).

* **QueryRewriter (`query_rewriter.py`)**

  * Decide si una query “necesita contexto” (pronombres, follow-up, demasiado corta).
  * Si aplica, genera una query mejorada usando un port minimalista (`generate_text`).
  * Protecciones:

    * feature flag (`enabled`).
    * requerimiento de historial mínimo.
    * límite de longitud y fallback a original ante error.

* **ChunkReranker (`reranker.py`)**

  * Problema que resuelve: el retrieval por embeddings es rápido pero no siempre el más relevante.
  * Modos:

    * `disabled`: mantiene orden.
    * `heuristic`: overlap + longitud + posición + `similarity` si existe.
    * `llm`: puntúa query+chunk con un LLM (más lento, más caro) y retorna `top_k`.
  * Límites defensivos:

    * no rerankea más de 20 chunks (`_MAX_CHUNKS_TO_RERANK`).

* **RateLimiter (`rate_limiting.py`)**

  * Control de cuota por scope `workspace` o `user`.
  * Recursos: `messages`, `tokens`, `uploads`.
  * Ventana: hoy está alineada a inicio de hora (ej: `YYYY-MM-DD HH:00`).
  * Devuelve `RateLimitResult` con `retry_after_seconds` para mapear a 429.
  * Storage se abstrae por port; `InMemoryQuotaStorage` es útil para tests/dev (no multi-proceso).

### Tecnologías/librerías (qué entra y qué no entra aquí)

* Este nivel está pensado para depender **solo** de:

  * Python estándar (dataclasses, datetime, uuid, regex, logging)
  * entidades/value objects/puertos del Dominio (`app/domain/...`)
  * utilidades crosscutting (settings, logger) *sin acoplarse al framework de entrada*
* Esta capa evita depender directamente de:

  * FastAPI/Starlette (Interfaces)
  * SQLAlchemy/psycopg (Infrastructure)
  * Redis SDK/S3 SDK/LLM SDK (Infrastructure)

---

## 🔗 Conexiones y roles

* **Rol arquitectónico:** Application Service Layer (orquestación + políticas).

* **Recibe órdenes de:**

  * Interfaces HTTP (`app/interfaces/...`) cuando llega un request.
  * Worker (`app/worker/...`) cuando se ejecuta un job.

* **Llama a:**

  * Dominio: entidades + puertos (repos/services) para reglas y contratos.
  * Infraestructura: *indirectamente* (la implementación concreta se inyecta desde `app/container.py`).

* **Límites (reglas de import que se esperan):**

  * Application **no** importa `interfaces/`.
  * Application **no** importa implementaciones concretas de `infrastructure/`.
  * Application puede importar `crosscutting` para settings/log (siempre que no implique acoplarse a HTTP).

---

## 👩‍💻 Guía de uso (Snippets)

> La idea de estos snippets es mostrar cómo se consume Application **sin HTTP**. Esto te permite testear o ejecutar lógica en integración/worker.

### 1) Construir contexto RAG con citas `[S#]` y `FUENTES`

```python
from app.application import ContextBuilder
from app.domain.entities import Chunk

builder = ContextBuilder(max_size=2000)

chunks = [
    Chunk(content="Política de vacaciones: 14 días.", document_title="RRHH", document_id="doc-1"),
    Chunk(content="Part-time también aplica.", document_title="RRHH", document_id="doc-1"),
]

context, used = builder.build(chunks)
print(used)
print(context)
```

### 2) Aplicar política de prompt-injection sobre chunks (exclude/downrank)

```python
from app.application import apply_injection_filter

# chunks debe venir con metadata precalculada (idealmente desde ingest)
filtered = apply_injection_filter(
    chunks=chunks,
    mode="downrank",
    threshold=0.6,
)
```

### 3) Rate limit por workspace usando storage in-memory (útil en tests)

```python
from uuid import uuid4

from app.application import InMemoryQuotaStorage, RateLimitConfig, RateLimiter

storage = InMemoryQuotaStorage()
limiter = RateLimiter(storage, RateLimitConfig(messages_per_hour=2))

workspace_id = uuid4()

check = limiter.check("messages", workspace_id=workspace_id)
assert check.allowed is True

limiter.record("messages", workspace_id=workspace_id, amount=1)
limiter.record("messages", workspace_id=workspace_id, amount=1)

blocked = limiter.check("messages", workspace_id=workspace_id)
print(blocked.allowed, blocked.retry_after_seconds)
```

---

## 🧩 Cómo extender sin romper nada

### A) Agregar un nuevo use case (recomendado: empezar por `usecases/`)

1. Elegí el bounded context correcto: `usecases/chat/`, `usecases/ingestion/`, `usecases/documents/`, `usecases/workspace/`.
2. Creá un archivo con verbo + sustantivo (ej: `archive_workspace.py`, `reprocess_document.py`).
3. Definí **Input/Result** tipados (dataclasses) y mantené el `execute(...)` como punto de entrada.
4. Validá al inicio (fail-fast): ids, permisos, invariantes de negocio y precondiciones.
5. Consumí **puertos** (repos/services) — si falta un puerto, crealo en `domain/`.
6. No hagas IO directo (ni SQL, ni Redis, ni filesystem): pedilo vía dependencias.
7. Exportá el use case en el `__init__.py` del submódulo si tiene que ser consumido desde fuera.
8. Registrá el wiring en `app/container.py` (dónde se instancian las dependencias concretas).

### B) Agregar/ajustar un servicio de Application (cuando se repite lógica en varios use cases)

1. Confirmá que no sea dominio puro (si es regla estable del negocio, debería ir en `domain/`).
2. Diseñalo como componente pequeño:

   * input claro
   * output tipado
   * sin side-effects
3. Agregá límites defensivos (max lengths, top_k, thresholds) y defaults seguros.
4. Si depende de un proveedor externo, modelalo como `Protocol` minimalista (port).
5. Exponelo desde `application/__init__.py` solo si es parte del “API pública” interna.

---

## 🆘 Troubleshooting

* **Síntoma:** `ValueError: Either user_id or workspace_id must be provided`

  * **Causa probable:** se invocó `RateLimiter.check/record()` sin scope.
  * **Solución:** decidir si el límite aplica por `workspace_id` (preferido en features multi-tenant) o por `user_id`.

* **Síntoma:** `ValueError: Unknown resource: <...>`

  * **Causa probable:** `RateLimiter` recibió un resource fuera de `{messages,tokens,uploads}`.
  * **Solución:** revisar el caller y estandarizar el nombre del recurso.

* **Síntoma:** `ValueError: Invalid injection filter mode: <...>`

  * **Causa probable:** mode distinto de `off/exclude/downrank`.
  * **Solución:** normalizar mode en settings y validar inputs antes de llamar.

* **Síntoma:** el contexto RAG sale vacío (`"", 0`)

  * **Causa probable:** `max_size` demasiado bajo o chunks vacíos.
  * **Solución:** revisar `settings.max_context_chars` y el contenido real del chunk; loggea `chunks_used`.

* **Síntoma:** `QueryRewriter` “no reescribe nunca”

  * **Causa probable:** feature deshabilitado, query larga (>= 50), o historial insuficiente.
  * **Solución:** revisar flags `enabled`, `min_history_messages` y la longitud de query.

* **Síntoma:** el reranker devuelve el mismo orden aunque esté activo

  * **Causa probable:** modo `disabled`, `top_k` chico, o chunks con contenido muy similar.
  * **Solución:** verificar `mode`, revisar `scores` en `RerankResult` y aumentar candidates (hasta 20).

---

## 🔎 Ver también

* [Use cases hub](./usecases/README.md)
* [Domain](../domain/README.md)
* [Infrastructure](../infrastructure/README.md)
* [Interfaces](../interfaces/README.md)
* [Composition root (`container.py`)](../container.py)
