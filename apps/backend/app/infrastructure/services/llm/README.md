# services

Como un **puente a proveedores externos**: encapsula SDKs (embeddings/LLM) y agrega resiliencia (retry) sin contaminar el dominio.

## 🎯 Misión

Este módulo implementa **adapters de infraestructura** para servicios externos definidos como puertos en el dominio (`EmbeddingService`, `LLMService`) y los complementa con utilidades de resiliencia (`retry`) y caching para embeddings.

Es el lugar donde vive lo que _sí depende_ de SDKs, claves, límites de APIs, y manejo de fallas de red, manteniendo a _Application_ y _Domain_ libres de esos detalles.

Recorridos rápidos por intención:

- **Quiero embeddings reales (Google) + límites + retry** → `google_embedding_service.py`
- **Quiero embeddings deterministas para tests/CI** → `fake_embedding_service.py`
- **Quiero cache-aside + deduplicación + métricas** → `cached_embedding_service.py`
- **Quiero LLM (Google/Fake) y streaming** → `llm/README.md`
- **Quiero política estándar de reintentos (tenacity)** → `retry.py`
- **Quiero ver cómo se eligen providers (feature flags)** → `../../container.py` (`get_embedding_service`, `get_llm_service`)

### Qué SÍ hace

- Implementa `EmbeddingService` con:
  - provider real (Google `text-embedding-004`) con validaciones de dimensionalidad y batch limit.
  - provider fake determinista para tests/CI.
  - decorator `CachingEmbeddingService` que agrega cache-aside + dedupe de batch + métricas.

- Implementa `LLMService` con:
  - provider real (Gemini) con prompts versionados + política “context-only”.
  - provider fake determinista que soporta streaming.

- Provee utilidades de resiliencia para llamadas externas:
  - clasificación de errores transitorios vs permanentes.
  - backoff exponencial con jitter y logging estructurado.

### Qué NO hace (y por qué)

- No contiene reglas de negocio.
  - **Razón:** el negocio vive en Domain/Application.
  - **Impacto:** este paquete no decide permisos, visibilidad, ni qué chunks usar; solo ejecuta IO externo y devuelve resultados.

- No expone endpoints HTTP ni DTOs HTTP.
  - **Razón:** Interfaces es el boundary de transporte.
  - **Impacto:** routers/adapters HTTP llaman a casos de uso; los casos de uso consumen estos servicios a través de puertos.

- No decide “qué provider usar” en runtime.
  - **Razón:** la decisión pertenece al composition root (container).
  - **Impacto:** la selección por flags (`fake_llm`, `fake_embeddings`) está en `../../container.py`.

## 🗺️ Mapa del territorio

| Recurso                       | Tipo           | Responsabilidad (en humano)                                                                                                     |
| :---------------------------- | :------------- | :------------------------------------------------------------------------------------------------------------------------------ |
| `__init__.py`                 | Archivo Python | Facade del paquete: re-exporta clases/funciones para imports estables (embeddings, LLM, retry).                                 |
| `cached_embedding_service.py` | Archivo Python | Decorator `CachingEmbeddingService`: cache-aside por clave estable, dedupe de batch y métricas hit/miss (best-effort).          |
| `fake_embedding_service.py`   | Archivo Python | `FakeEmbeddingService`: embeddings deterministas (SHA-256) con dimensión configurable (default 768) para tests/CI.              |
| `google_embedding_service.py` | Archivo Python | `GoogleEmbeddingService`: adapter Google GenAI `text-embedding-004`, task_type query/document, batch limit y retry transitorio. |
| `llm/`                        | Carpeta        | Implementaciones de `LLMService`: Google (Gemini) y fake determinista con soporte de streaming.                                 |
| `retry.py`                    | Archivo Python | Helper de resiliencia: política de transitorios/permanentes + decorator de tenacity con backoff+jitter y logs por intento.      |
| `README.md`                   | Documento      | Portada + guía de navegación del paquete.                                                                                       |

## ⚙️ ¿Cómo funciona por dentro?

Explicación técnica en formato Input → Proceso → Output, con los flujos que se repiten en este paquete.

### Embeddings (puerto `domain.services.EmbeddingService`)

**Input**

- `embed_query(query: str)` para búsqueda.
- `embed_batch(texts: list[str])` para ingesta (chunking → embeddings).

**Proceso**

1. **Selección de provider (composition root)**
   - `get_embedding_service()` en `../../container.py` decide:
     - si `Settings.fake_embeddings` está activo → usa `FakeEmbeddingService`.
     - si no → usa `GoogleEmbeddingService`.

   - En ambos casos, el provider queda envuelto por `CachingEmbeddingService`.

2. **Provider real (Google)** — `google_embedding_service.py`
   - Modelo default: `text-embedding-004`.
   - Dimensionalidad esperada: `768` (validación activa por default).
   - Límite de batch: `10` textos por request (`BATCH_LIMIT`).
   - Diferencia task type:
     - `retrieval_query` para `embed_query`.
     - `retrieval_document` para `embed_batch`.

   - Manejo de errores:
     - envuelve la llamada a `client.models.embed_content` con retry (`create_retry_decorator()` de `retry.py`).
     - transforma fallas genéricas en `EmbeddingError` (sin ocultar el origen: `raise ... from exc`).

   - Clave:
     - si no se inyecta `api_key`, lee `GOOGLE_API_KEY` desde environment.

3. **Provider fake** — `fake_embedding_service.py`
   - No hace IO.
   - Genera un vector determinista derivado del texto (`SHA-256(text|index)`), útil para:
     - tests unitarios sin credenciales.
     - CI.
     - pruebas de caching/dedupe.

   - Default: 768 dimensiones para que encaje con la DB (`vector(768)`).

4. **Caching/Dedupe** — `cached_embedding_service.py`
   - Implementa **cache-aside**:
     - `cache.get(key)` → hit: return.
     - miss: llama al provider, luego `cache.set(key, embedding)`.

   - **Clave de cache estable** (`build_embedding_cache_key`):
     - `model_id | task_type | normalization_version | normalized_text`.
     - normalización v1: `strip()` + colapsar whitespace múltiple.

   - **Batch dedupe**:
     - si el mismo texto aparece N veces en `texts`, se pide 1 embedding y se replica en la salida (mantiene el orden original 1:1).

   - **Best-effort**:
     - si `cache.get/set` falla (Redis caído, etc.), se loguea y se continúa con el provider (no se rompe el flujo).

   - **Métricas**:
     - registra `record_embedding_cache_hit/miss` (kind=query/batch y count para duplicados).

**Output**

- `list[float]` o `list[list[float]]` con tamaño consistente.
- Errores tipados: `EmbeddingError`.

Nota sobre la cache concreta:

- El container inyecta `get_embedding_cache()` desde `../cache.py`.
- Esa fachada hashea internamente la entrada (SHA-256) antes de ir a Redis/memoria.
  - Si `CachingEmbeddingService` le pasa una clave compuesta, la fachada la hashea igual.
  - Funciona, pero las keys finales en Redis no son “human-readable”.

### LLM (puerto `domain.services.LLMService`)

**Input**

- `generate_answer(query: str, context: str)` para respuesta RAG sin streaming.
- `generate_text(prompt: str, max_tokens: int = 200)` para tareas auxiliares (rewrites, resúmenes).
- `generate_stream(query: str, chunks: list[Chunk])` para UX streaming.

**Proceso**

1. **Selección de provider (composition root)**
   - `get_llm_service()` en `../../container.py` decide:
     - `Settings.fake_llm` → `FakeLLMService`.
     - si no → `GoogleLLMService`.

2. **Provider real (Google Gemini)** — `llm/google_llm_service.py`
   - Modelo default: `gemini-1.5-flash` (`DEFAULT_MODEL_ID`).
   - API key:
     - si no se inyecta `api_key`, lee `GOOGLE_API_KEY` desde environment.

   - Prompts versionados:
     - usa `PromptLoader` (`../prompts/`) para armar el prompt final (`context` + `query`).
     - expone `prompt_version` para logs/observabilidad.

   - Política “context-only”:
     - si `context` está vacío → no llama al LLM y devuelve un fallback fijo (evita alucinaciones).
     - en streaming, si el contexto construido está vacío → emite el fallback y termina.

   - Streaming:
     - reintenta solo la **creación** del stream (errores al iniciar).
     - durante la iteración no reintenta: no hay idempotencia si ya se emitieron tokens.

   - Context builder:
     - recibe `chunks` en `generate_stream` y construye `context` con un `ContextBuilderPort`.
     - si no se inyecta, usa un fallback con import lazy a `application.context_builder`.

3. **Provider fake** — `llm/fake_llm.py`
   - No hace IO.
   - Respuesta determinista por hash de (`query|context`).
   - Streaming determinista (emite trozos de tamaño fijo).
   - Expone `model_id` y `prompt_version` estables para asserts en tests.

**Output**

- `str` o `AsyncGenerator[str, None]`.
- Errores tipados: `LLMError`.

### Retry / resiliencia (`retry.py`)

**Input**

- Funciones que llaman proveedores externos (SDKs, HTTP, etc.).

**Proceso**

- `is_transient_error(exc)` clasifica errores en orden:
  1. status code HTTP (si existe):
     - `400/401/403/404` → permanente (fail-fast).
     - `408/429/500/502/503/504` → transitorio (reintentar).

  2. tipos built-in (timeouts/connection/OSError) → transitorio.
  3. heurística por nombre/mensaje (best-effort) para SDKs poco tipados.
  4. default conservador → no reintentar.

- `create_retry_decorator()` construye un decorator de `tenacity` con:
  - `stop_after_attempt(Settings.retry_max_attempts)`.
  - `wait_exponential_jitter(initial=Settings.retry_base_delay_seconds, max=Settings.retry_max_delay_seconds)`.
  - logging de cada intento (`before_sleep`).
  - `reraise=True` (propaga la última excepción).

- `with_retry(func)` aplica el decorator por default y evita redefinir closures en cada llamada.

**Output**

- Misma firma de la función original, con reintentos aplicados.

## 🔗 Conexiones y roles

- **Rol arquitectónico:** _Infrastructure_ (adapters a proveedores externos).

- **Recibe órdenes de:**
  - Casos de uso en `application/` (ingestion, query answering, rewrites/rerank).
  - Composition root (`../../container.py`) que instancia y configura.

- **Llama a:**
  - SDK Google GenAI (`google.genai.Client`) en providers reales.
  - `../prompts/` para templates versionados del LLM.
  - `../cache.py` (vía container) para backend de cache.
  - `../../crosscutting/config.py` (vía `get_settings()`) para parámetros de retry.
  - `../../crosscutting/logger.py` y `../../crosscutting/metrics.py` para observabilidad.

- **Reglas de límites (imports/ownership):**
  - Este paquete no debe importar routers/DTOs de `interfaces/`.
  - No debe contener lógica de negocio (RBAC, policy, decisiones de retrieval).
  - Nota actual: `GoogleLLMService` tiene un fallback con import lazy a `application.context_builder` si no se inyecta `context_builder`.
    - Mantiene el módulo usable sin wiring extra, pero el camino “limpio” es inyectar el builder desde el container.

## 👩‍💻 Guía de uso (Snippets)

### 1) Selección por flags desde el container (runtime)

```python
from app.container import get_embedding_service, get_llm_service

embeddings = get_embedding_service()  # puede ser Google o Fake + cache
llm = get_llm_service()              # puede ser Google o Fake
```

### 2) Embeddings con cache-aside explícito (útil en pruebas)

```python
from app.infrastructure.cache import get_embedding_cache
from app.infrastructure.services import CachingEmbeddingService, FakeEmbeddingService

service = CachingEmbeddingService(
    provider=FakeEmbeddingService(),
    cache=get_embedding_cache(),
)

v1 = service.embed_query("hola")
v2 = service.embed_query("hola")  # hit (si cache funciona)
```

### 3) Inyectar `client` en providers reales (tests sin red)

```python
from google import genai

from app.infrastructure.services import GoogleEmbeddingService

# Cliente fake/mockeado o configurado para sandbox; se inyecta para no depender de env vars.
client = genai.Client(api_key="test-key")
service = GoogleEmbeddingService(client=client, expected_dimensions=768)
```

### 4) Aplicar retry a una función cualquiera (SDK/HTTP)

```python
from app.infrastructure.services import with_retry

@with_retry
def call_external(*, request_id: str) -> str:
    # request_id via kwargs mejora trazabilidad en logs de retry
    return "ok"

call_external(request_id="req-123")
```

## 🧩 Cómo extender sin romper nada

Checklist práctico para sumar un provider nuevo sin romper import paths ni tests.

### Agregar un provider de embeddings

1. **Implementación:** crear `openai_embedding_service.py` (por ejemplo) implementando `domain.services.EmbeddingService`.
2. **Compatibilidad:**
   - respetar `embed_query` y `embed_batch`.
   - validar dimensionalidad esperada (alineada a DB / repositorios).
   - definir `model_id` estable (lo usa `CachingEmbeddingService` para namespacing de cache keys).

3. **Resiliencia:** envolver la llamada externa con `create_retry_decorator()` o `with_retry`.
4. **Export:** agregar el export en `__init__.py` y en `__all__`.
5. **Wiring:** actualizar `get_embedding_service()` en `../../container.py`:
   - sumar una feature flag (en `../../crosscutting/config.py`) si hay múltiples providers.
   - mantener `CachingEmbeddingService` como wrapper (si aplica).

6. **Tests:**
   - unit: asserts de validaciones (input vacío, batch size mismatch, dimensiones).
   - integration (opcional): si hay provider real, tests marcados/skipped por credenciales.

### Agregar un provider de LLM

1. **Implementación:** agregar un archivo en `llm/` que implemente `domain.services.LLMService`.
2. **Prompts:**
   - si usa prompts versionados, reutilizar `PromptLoader` (`../prompts/`).
   - exponer `model_id` y `prompt_version` para observabilidad.

3. **Streaming:**
   - definir claramente qué se reintenta (crear stream) y qué no (iteración).

4. **Wiring:** actualizar `get_llm_service()` en `../../container.py` y sumar flag si corresponde.

### Extender retry (política)

1. Agregar status codes o heurísticas en `retry.py`.
2. Mantener el default conservador: si no es claramente transitorio, no reintentar.
3. Ajustar settings en `../../crosscutting/config.py` si necesitás más intentos o delays.

## 🆘 Troubleshooting

- **`GOOGLE_API_KEY not configured` al iniciar** → falta `GOOGLE_API_KEY` en environment y no se inyectó `client`/`api_key` → revisar `.env` + `google_embedding_service.py` / `llm/google_llm_service.py`.
- **Embeddings con dimensión inesperada** (`expected 768, got X`) → provider/model cambiado o configuración incorrecta → revisar `GoogleEmbeddingService(expected_dimensions=...)` y el modelo activo (`model_id`).
- **Errores por batch grande en embeddings** → el provider parte en batches de `BATCH_LIMIT=10`, pero si se cambió el límite y falla → revisar `google_embedding_service.py` (`BATCH_LIMIT`, `batch_limit`).
- **Cache “no pega” nunca** (todo miss) → backend reinicia (in-memory por proceso) o Redis no está disponible → revisar `../cache.py` (autodetección por `REDIS_URL`) y logs de `Embedding cache get failed` en `cached_embedding_service.py`.
- **Cache rompe el flujo** → no debería; cache es best-effort. Si está rompiendo, el error viene del provider o de validaciones (input vacío) → revisar excepciones `EmbeddingError` en `cached_embedding_service.py`.
- **Retry reintenta cosas que no debería** → revisar `is_transient_error()` (status codes, heurísticas) y `PERMANENT_HTTP_CODES` / `TRANSIENT_HTTP_CODES`.
- **Streaming falla a mitad de respuesta** → no hay retry durante iteración del stream → revisar `llm/google_llm_service.py` y logs `Streaming failed`.
- **Import cycles o comportamiento raro con context builder** → `GoogleLLMService` hace import lazy a `application.context_builder` si no se inyecta builder → preferir inyección desde `../../container.py` para evitar sorpresas.
- **Prompts no encontrados / versión inválida** → `PromptLoader` depende de `Settings.prompt_version` y archivos en `../prompts/` → revisar `../prompts/README.md`, `../prompts/loader.py` y `../../crosscutting/config.py`.

## 🔎 Ver también

- `./llm/README.md` (implementaciones LLM y streaming)
- `../prompts/README.md` (prompts versionados y loader)
- `../cache.py` (backends Redis/in-memory, TTL y autodetección por `REDIS_URL`)
- `../../domain/services.py` (puertos `EmbeddingService` / `LLMService`)
- `../../domain/cache.py` (puerto `EmbeddingCachePort`)
- `../../crosscutting/config.py` (flags `fake_llm` / `fake_embeddings` y settings de retry)
- `../../container.py` (wiring y selección de providers)
- `../../crosscutting/metrics.py` (métricas de cache hit/miss)
