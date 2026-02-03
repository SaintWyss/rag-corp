# Infrastructure Services
Como un **puente con amortiguadores**: traduce pedidos del sistema a llamadas a proveedores externos (Google) y vuelve con embeddings/texto, con **cache** y **retry** para resistir fallas de red sin contaminar Domain/Application.

## 🎯 Misión

Este módulo implementa **adapters concretos** de servicios externos que el dominio define como puertos (embeddings y LLM). Acá viven los detalles que no deben filtrarse hacia Application/Domain: SDKs, API keys, límites de batch, validaciones de forma, reintentos y observabilidad asociada.

Recorridos rápidos por intención:

- **Quiero embeddings reales (Google) + validación + retry** → `google_embedding_service.py`
- **Quiero embeddings deterministas para tests/CI** → `fake_embedding_service.py`
- **Quiero cache-aside + dedupe en batch + métricas** → `cached_embedding_service.py`
- **Quiero LLM (Google/Fake) y streaming** → `llm/README.md`
- **Quiero política estándar de reintentos (tenacity)** → `retry.py`
- **Quiero ver cómo se elige “fake vs real”** → `../../container.py` (`get_embedding_service`, `get_llm_service`)

### Qué SÍ hace

- Implementa `EmbeddingService` con:
- provider real (Google `text-embedding-004`) con validación de dimensionalidad y batch limit.
- provider fake determinista para tests/CI.
- decorator `CachingEmbeddingService` que agrega cache-aside + dedupe de batch + métricas.

- Implementa `LLMService` con:
- provider real (Gemini) con prompts versionados + política “context-only”.
- provider fake determinista que soporta streaming.

- Provee utilidades de resiliencia para llamadas externas:
- clasificación de errores transitorios vs permanentes.
- backoff exponencial con jitter y logging estructurado.

### Qué NO hace (y por qué)

- No contiene reglas de negocio ni decide políticas (auth/retrieval/visibilidad). Razón: ** esas decisiones viven en Domain/Application. Impacto: ** este módulo no decide permisos, no elige chunks ni reordena resultados; solo ejecuta IO externo de forma segura.

- No expone endpoints HTTP ni DTOs HTTP. Razón: ** Interfaces es el boundary de transporte. Impacto: ** routers/adapters HTTP llaman a casos de uso; los casos de uso consumen estos adapters por puertos.

- No decide qué provider usar en runtime. Razón: ** la decisión pertenece al composition root (container). Impacto: ** la selección real/fake se hace en `../../container.py` usando flags de `Settings`.

## 🗺️ Mapa del territorio

| Recurso | Tipo | Responsabilidad (en humano) |
| :---------------------------- | :------------- | :-------------------------------------------------------------------------------------------------------------------- |
| `__init__.py` | Archivo Python | Facade del paquete: re-exporta clases/funciones para imports estables (embeddings, LLM, retry). |
| `cached_embedding_service.py` | Archivo Python | Decorator `CachingEmbeddingService`: cache-aside, dedupe de batch, orden estable y métricas hit/miss. |
| `fake_embedding_service.py` | Archivo Python | `FakeEmbeddingService`: embeddings deterministas (hash) para tests/CI sin red ni credenciales. |
| `google_embedding_service.py` | Archivo Python | `GoogleEmbeddingService`: embeddings reales vía Google GenAI (`text-embedding-004`), batch limit y retry transitorio. |
| `llm` | Carpeta | Implementaciones `LLMService` (Google + Fake) y documentación específica del submódulo. |
| `README.md` | Documento | Portada + navegación y contratos de uso del paquete. |
| `retry.py` | Archivo Python | Política y utilities de retry: transient/permanent + decorator tenacity con backoff+jitter. |

## ⚙️ ¿Cómo funciona por dentro?

### Panorama: wiring real en runtime (container)

Este paquete es infraestructura pura: las instancias se crean desde `app/container.py`.

- `get_embedding_service()`:
  1. Lee `Settings.fake_embeddings`.
  2. Elige `FakeEmbeddingService()` o `GoogleEmbeddingService()`.
  3. Envuelve el provider con `CachingEmbeddingService(provider=..., cache=get_embedding_cache())`.

- `get_llm_service()`:
  1. Lee `Settings.fake_llm`.
  2. Elige `FakeLLMService()` o `GoogleLLMService()`.

Eso mantiene a Application consumiendo solo interfaces (`EmbeddingService`, `LLMService`) y evita imports de SDKs fuera de Infrastructure.

---

### Embeddings: `CachingEmbeddingService` (decorator) + provider (Google/Fake)

#### Input

- `embed_query(query: str)` → embedding para búsqueda (modo query).
- `embed_batch(texts: Sequence[str])` → embeddings para ingesta (modo document).

#### Proceso (cache-aside + dedupe)

`cached_embedding_service.py` implementa un flujo fijo:

1. **Validaciones fail-fast**
- Query vacía → `EmbeddingError("Query must not be empty")`.
- En batch, texto vacío → `EmbeddingError(f"Batch text at index {i} must not be empty")`.

2. **Construcción de clave estable**
- Normaliza texto (v1): `strip()` + colapsa whitespace múltiple.
- Key = `"{model_id}|{task_type}|{normalization_version}|{normalized_text}"`.
- `task_type` separa embeddings por uso:
- `retrieval_query` (búsqueda)
- `retrieval_document` (ingesta)

3. **Cache GET (best-effort)**
- Si `cache.get(key)` falla (Redis caído, etc.), se loguea warning y se trata como miss.
- Hit:
- registra `record_embedding_cache_hit(kind="query"|"batch", count=...)`.
- devuelve embedding cacheado.

4. **Provider call (solo si miss)**
- Query → `provider.embed_query(query)`.
- Batch → dedupe: si el mismo texto aparece N veces, se pide 1 embedding y se replica manteniendo orden 1:1.
- Se valida integridad: `len(embeddings) == len(miss_texts)`.

5. **Cache SET (best-effort)**
- Si `cache.set(key, embedding)` falla, se loguea warning y se sigue.
- La cache no puede romper el pipeline de embeddings.

#### Output

- `embed_query` → `list[float]`
- `embed_batch` → `list[list[float]]` (mismo orden y cardinalidad que el input)
- Errores tipados: `EmbeddingError` (con `raise ... from exc` cuando el origen es externo)

> Nota sobre la cache concreta: el `cache` suele venir de `app/infrastructure/cache.py` (`get_embedding_cache()`). Esa fachada hashea internamente la clave (SHA-256) antes de persistir, evitando guardar texto sensible como key. Funciona igual con `CachingEmbeddingService`, pero las keys finales en Redis no son human-readable.

---

### Provider real: `GoogleEmbeddingService` (Google GenAI)

`google_embedding_service.py` implementa `EmbeddingService` usando `google.genai`.

#### Input

- `embed_query(query)` y `embed_batch(texts)`.

#### Proceso

1. **API key**
- Usa `api_key` inyectada o `GOOGLE_API_KEY` desde environment.
- Sin key y sin `client` → `EmbeddingError("GOOGLE_API_KEY not configured")`.

2. **Límites y batching**
- `BATCH_LIMIT = 10`.
- Parte `texts` en lotes preservando orden.

3. **Task type por modo**
- query: `retrieval_query`.
- document: `retrieval_document`.

4. **Retry integrado**
- Envuelve `client.models.embed_content` con `create_retry_decorator()` de `retry.py`.

5. **Validaciones de respuesta**
- cardinalidad 1:1 con inputs.
- `values` presente.
- dimensión esperada por default: `768` (configurable; si `expected_dimensions=None`, no valida).

#### Output

- Vectores de floats (768 dims por defecto).
- Errores tipados: `EmbeddingError` con logs estructurados (model_id, task_type, batch_size).

---

### Provider fake: `FakeEmbeddingService` (determinista)

`fake_embedding_service.py` genera embeddings por hash.

- No hace IO.
- Default `dimension=768` para compatibilidad.
- Deriva un vector estable de `sha256(text|index)` y lo mapea a floats.
- Útil para unit tests, CI y pruebas del cache/dedupe.

---

### LLM: `GoogleLLMService` / `FakeLLMService` (submódulo `llm/`)

#### Input

- `generate_answer(query: str, context: str) -> str`
- `generate_text(prompt: str, max_tokens: int = 200) -> str`
- `generate_stream(query: str, chunks: list[Chunk]) -> AsyncGenerator[str, None]`

#### Proceso: Google (`llm/google_llm_service.py`)

1. **API key**
- `api_key` o `GOOGLE_API_KEY`, o `client` inyectado.

2. **Prompts versionados**
- Usa `PromptLoader` desde `app/infrastructure/prompts`.
- Expone `prompt_version` para observabilidad.

3. **Context-only policy (anti-alucinación)**
- Si el `context` está vacío: devuelve fallback fijo (no llama al LLM).
- En streaming: si el context construido queda vacío: emite fallback y termina.

4. **Retry**
- Reintenta al iniciar.
- En streaming no reintenta durante iteración (no hay idempotencia del output).

5. **Context builder para streaming**
- Usa `ContextBuilderPort` para `chunks -> (context, chunks_used)`.
- Si no se inyecta, usa fallback con import lazy a `application.context_builder`.

#### Proceso: Fake (`llm/fake_llm.py`)

- Determinista por hash de `query|context`.
- Soporta streaming emitiendo trozos de tamaño fijo.

#### Output

- Texto (sync) o stream (async), con errores tipados `LLMError`.

---

### Retry / resiliencia (`retry.py`)

#### Input

Funciones que llaman proveedores externos (SDKs/HTTP).

#### Proceso

- `is_transient_error(exc)` clasifica fallas:
- permanentes: 400/401/403/404 (fail-fast).
- transitorias: 408/429/5xx, timeouts, connection errors.
- heurística best-effort para SDKs poco tipados.

- `create_retry_decorator()` construye tenacity:
- `stop_after_attempt(Settings.retry_max_attempts)`.
- backoff exponencial con jitter (initial/max desde Settings).
- logs por intento (before_sleep).
- `reraise=True`.

- `with_retry` aplica la política por default a funciones.

#### Output

La misma salida de la función original, con reintentos aplicados.

## 🔗 Conexiones y roles

- **Rol arquitectónico:** Infrastructure (adapters a servicios externos + resiliencia).

- **Recibe órdenes de:**
- Application use cases (ingestion, answering, rewrites, etc.) vía puertos del dominio.
- `app/container.py` (composition root) para instanciar/configurar.

- **Llama a:**
- Google GenAI SDK (`google.genai.Client`).
- `app/infrastructure/prompts` para templates versionados.
- `app/infrastructure/cache.get_embedding_cache()` para caching.
- `app/crosscutting/config.get_settings()` para retry.
- `app/crosscutting/logger` y `app/crosscutting/metrics` para observabilidad.

- **Reglas de límites (imports/ownership):**
- No importa routers/DTOs HTTP de `interfaces/`.
- No implementa lógica de negocio (RBAC, policy, decisiones de retrieval).
- Fallback actual: `GoogleLLMService` hace import lazy a `application.context_builder` si no se inyecta builder. La vía limpia es inyectarlo desde el container.

## 👩‍💻 Guía de uso (Snippets)
```python
# Por qué: muestra el contrato mínimo del módulo.
from app.container import get_embedding_service, get_llm_service

emb = get_embedding_service()
llm = get_llm_service()
vec = emb.embed_query("hola")
text = llm.generate_text("resumí...")
```

```python
# Por qué: ejemplo de integración sin infraestructura real.
from app.infrastructure.services import CachingEmbeddingService, FakeEmbeddingService
from app.infrastructure.cache import get_embedding_cache

svc = CachingEmbeddingService(provider=FakeEmbeddingService(), cache=get_embedding_cache())
```

```python
# Por qué: deja visible el flujo principal.
from app.infrastructure.services import with_retry

@with_retry
def call_external():
    return "ok"
```

## 🧩 Cómo extender sin romper nada
- Implementá un provider nuevo que cumpla `EmbeddingService` o `LLMService`.
- Validá inputs (empty query) y dimensiones esperadas.
- Envolvé llamadas externas con `retry.py`.
- Cableá selección en `app/container.py`.
- Tests: unit en `apps/backend/tests/unit/infrastructure/`, integration si usa red real.

## 🆘 Troubleshooting
- **Síntoma:** `GOOGLE_API_KEY not configured`.
- **Causa probable:** API key faltante.
- **Dónde mirar:** `.env` y `crosscutting/config.py`.
- **Solución:** setear `GOOGLE_API_KEY` o habilitar fake.
- **Síntoma:** dimensión de embedding incorrecta.
- **Causa probable:** modelo desalineado con DB (768).
- **Dónde mirar:** `google_embedding_service.py` y repositorio Postgres.
- **Solución:** alinear modelo/dimensión.
- **Síntoma:** cache no pega.
- **Causa probable:** cache backend caído.
- **Dónde mirar:** `infrastructure/cache.py`.
- **Solución:** revisar Redis o usar in-memory.
- **Síntoma:** streaming corta.
- **Causa probable:** error durante iteración.
- **Dónde mirar:** `services/llm`.
- **Solución:** revisar logs y provider.

## 🔎 Ver también
- `./llm/README.md`
- `../cache.py`
- `../prompts/README.md`
- `../../domain/services.py`
- `../../container.py`
