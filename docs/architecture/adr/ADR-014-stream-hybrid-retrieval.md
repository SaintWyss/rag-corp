# ADR-014: Streaming Endpoint Reusa SearchChunksUseCase con Hybrid Retrieval

## Estado

**Aceptado** (2026-02)

## Contexto

El endpoint `/ask/stream` (SSE) necesita hybrid retrieval (FTS+RRF, ADR-012) con la misma calidad que el endpoint síncrono `/ask`. Se evaluó cómo incorporar esa capacidad al path de streaming.

### Arquitectura existente

| Endpoint      | Use Case              | Retrieval      | Streaming |
| ------------- | --------------------- | -------------- | --------- |
| `/ask`        | `AnswerQueryUseCase`  | dense + hybrid | No        |
| `/query`      | `SearchChunksUseCase` | dense + hybrid | No        |
| `/ask/stream` | `SearchChunksUseCase` | dense + hybrid | SSE       |

El router de streaming (`query.py`) ya usaba `SearchChunksUseCase` para retrieval y luego delegaba a `stream_answer()` (SSE) para la generación. `SearchChunksUseCase` ya estaba wired en `container.py` con `enable_hybrid_search` y `RankFusionService`.

Existía un archivo `StreamAnswerQueryUseCase` (443 líneas) con Protocols propios (`EmbeddingPort`, `ChunkRetrievalPort`, `LLMStreamingPort`), pero **no era usado por ningún endpoint** y **no tenía soporte híbrido**.

### Opciones evaluadas

| Opcion                                           | Pros                                  | Contras                                          |
| ------------------------------------------------ | ------------------------------------- | ------------------------------------------------ |
| Actualizar `StreamAnswerQueryUseCase` con hybrid | Use case dedicado para streaming      | Duplicar lógica de retrieval, mantener dos paths |
| **Confirmar reuso de `SearchChunksUseCase`**     | Zero cambios en pipeline, consistente | Streaming no tiene use case propio               |

## Decision

Opcion 2: **confirmar que `/ask/stream` ya reusa `SearchChunksUseCase`** con hybrid retrieval, y agregar observabilidad para rastrear el uso.

### Cambios realizados

1. **Observabilidad**: nueva metrica `rag_hybrid_retrieval_total{endpoint}` (Prometheus counter) que distingue uso hibrido por endpoint (`ask` | `ask_stream`).
2. **Metadata flag**: `hybrid_used: bool` en `SearchChunksResult.metadata` y `AnswerQueryResult.metadata` para que los endpoints lean si se uso hybrid.
3. **Eliminacion de codigo muerto**: `StreamAnswerQueryUseCase` eliminado. No tenia consumidores y no soportaba hybrid.
4. **Tests**: `TestStreamingHybridIntegration` valida que `SearchChunksUseCase` aplica hybrid en el path de streaming (ON/OFF/fallback/metadata).

## Consecuencias

### Positivas

- Zero cambios en el pipeline de retrieval: el streaming obtiene la misma calidad dense+sparse+RRF que `/ask`.
- Observable: se puede distinguir en Grafana/Prometheus cuantos requests hibridos vienen de streaming vs sync.
- Codigo muerto eliminado: 443 lineas de `StreamAnswerQueryUseCase` que podian confundir.

### Negativas

- Si en el futuro se necesita un use case de streaming con logica de retrieval diferenciada, hay que crearlo desde cero.
- El streaming depende de la composicion en el router (no tiene un use case propio que encapsule retrieval + generacion).

## Ver tambien

- [ADR-012: Hybrid Retrieval con RRF](ADR-012-hybrid-retrieval-rrf.md)
- `app/application/usecases/chat/search_chunks.py`
- `app/interfaces/api/http/routers/query.py`
- `app/crosscutting/streaming.py`
