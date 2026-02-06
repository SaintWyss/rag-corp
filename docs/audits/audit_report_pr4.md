# Auditoría Técnica: `feat/rag-stream-hybrid` (PR4)

## A) Resumen Ejecutivo

- **Estado**: ✅ **READY FOR MERGE**.
- **Propósito**: Habilita la búsqueda híbrida (Vector + Full-Text + RRF) en el endpoint de streaming `/ask/stream`.
- **Unificación**: Elimina lógica duplicada. En lugar de tener un `StreamAnswerQueryUseCase` separado, el router usa `SearchChunksUseCase` (que ya tiene hybrid) y delega el streaming al helper `stream_answer`.
- **Testing**: Tests exhaustivos que validan que el flujo `stream -> search -> hybrid` funciona integrado y mantiene gracefully degradation.
- **Observabilidad**: Se registraron métricas de uso híbrido (`hybrid_used=True`) en los metadatos de respuesta y logs.

## B) Tabla de Cambios

| Archivo                                                             | Tipo     | Propósito                                                                                             |
| :------------------------------------------------------------------ | :------- | :---------------------------------------------------------------------------------------------------- |
| `apps/backend/app/interfaces/api/http/routers/query.py`             | API      | Router invoca `SearchChunksUseCase` y pasa resultados a `stream_answer`. Verifica flag `hybrid_used`. |
| `apps/backend/app/application/usecases/chat/search_chunks.py`       | Use Case | Agrega metadata `hybrid_used` al resultado para traza de audítoria.                                   |
| `apps/backend/tests/unit/application/test_hybrid_search.py`         | Test     | Nuevos tests: `TestStreamingHybridIntegration`. Valida wiring correcto.                               |
| `docs/architecture/adr/ADR-014-stream-hybrid-retrieval.md`          | Doc      | Documenta la decisión de unificar el retrieval en un solo Use Case.                                   |
| `apps/backend/app/application/usecases/chat/stream_answer_query.py` | Delete   | Clase eliminada. Código muerto (buena limpieza).                                                      |

## C) Evaluación Técnica

### 1. Wiring y Arquitectura

- **Correctitud**: La integración es limpia. En lugar de duplicar la lógica de retrieval en un "Stream UseCase", el router `/ask/stream` compone:
  1.  `SearchChunksUseCase.execute(...)` -> Obtiene chunks (Dense / Hybrid).
  2.  `stream_answer(...)` -> Genera SSE con LLM.
- **Ventaja**: Cualquier mejora futura al retrieval (ej: nuevos rerankers, filtros) beneficia automáticamente tanto al chat normal (`/ask`) como al streaming (`/ask/stream`).

### 2. Flags y Fallbacks

- **Hybrid Flag**: Los tests confirman que si `enable_hybrid_search=False` o falta dependencia, hace fallback transparente a Dense Only.
- **Sparse Failure**: Si FTS falla (DB error), atrapa excepción y retorna Dense Only. El stream no se corta.

### 3. Contratos y API

- **Compatibilidad**: No cambia el contrato SSE del frontend (eventos `sources`, `token`, `done`).
- **Metadata**: Expone `hybrid_used` en los logs del backend, útil para debuggear si RRF está actuando.

## D) Matriz de Riesgos

| Riesgo                 | Impacto                            | Probabilidad | Mitigación                                                                                              |
| :--------------------- | :--------------------------------- | :----------- | :------------------------------------------------------------------------------------------------------ |
| **Latencia en Stream** | TTFT (Time To First Token) aumenta | Media        | Hybrid hace 2 queries DB + RRF. Es más lento que solo Dense. Mitigación: Monitorear `retrieve_seconds`. |
| **RRF Tuning**         | Resultados irrelevantes al tope    | Baja         | RRF k=60 es safe default. Requiere feedback loop para ajustar `k` (fuera del scope de este PR).         |

## E) Estabilidad y Tests

- **Cobertura**: `test_hybrid_search.py` cubre específicamente la ruta de streaming.
- **Flakeness**: Baja. Los tests usan mocks determinísticos para embedding y repo.

## F) Veredicto

# ✅ GO

Cambio arquitectónicamente sólido (DRY), elimina código muerto y extiende la funcionalidad crítica (Hybrid Search) a la experiencia de usuario principal (Streaming).
