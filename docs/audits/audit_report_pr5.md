# Auditoría Técnica: `feat/rag-observability-stages` (PR5)

## A) Resumen Ejecutivo

- **Estado**: ✅ **READY FOR MERGE**.
- **Propósito**: Instrumentación granular de las etapas internas del pipeline RAG (Dense vs Sparse vs Fusion vs Rerank). Permite identificar cuellos de botella específicos que antes quedaban ocultos bajo "búsqueda".
- **Implementación**: Histograms dedicados con buckets ajustados a la latencia esperada de cada sub-etapa (microsegundos para Fusion, milisegundos para Rerank).
- **Resiliencia**: Captura fallos en etapas opcionales (Sparse, Rerank) mediante contadores de fallback (`rag_retrieval_fallback_total`), asegurando degradación grácil sin pérdida de servicio.
- **Documentación**: Runbook actualizado con tabla de métricas, umbrales sugeridos y queries PromQL.

## B) Tabla de Cambios

| Archivo                                      | Rol   | Detalle                                                                          |
| :------------------------------------------- | :---- | :------------------------------------------------------------------------------- |
| `app/crosscutting/metrics.py`                | Infra | Define Histograms (`_sparse_latency`, `_fusion_latency`, etc.) y buckets custom. |
| `app/usecases/chat/search_chunks.py`         | Logic | Mide tiempos con `perf_counter` alrededor de llamadas IO/CPU. Maneja fallbacks.  |
| `app/usecases/chat/answer_query.py`          | Logic | Mide reranking post-retrieval.                                                   |
| `tests/.../test_pipeline_instrumentation.py` | Test  | Tests unitarios mocking de métricas para verificar que se registran.             |
| `docs/runbook/observability.md`              | Doc   | Agrega referencia de nuevas métricas y paneles sugeridos.                        |

## C) Evaluación Técnica

### 1. Calidad de Métricas y Naming

- **Convención**: Sigue las mejores prácticas de Prometheus (`rag_<stage>_latency_seconds`).
- **Buckets**: Excelente decisión de desagregar.
  - `Fusion` (CPU-bound, rápido): buckets desde 100μs.
  - `Rerank` (GPU/Model-bound, lento): buckets hasta 1s.
  - Usar un solo histograma hubiera distorsionado la distribución.
- **Cardinalidad**: **Segura**.
  - El contador de fallbacks usa un label `stage` con valores fijos ("sparse", "rerank"). No hay values dinámicos (ids, queries).

### 2. Impacto en Performance

- **Overhead**: Despreciable. Uso de `time.perf_counter()` y actualización de registros en memoria.
- **Resiliencia**: La lógica de fallback en `search_chunks.py` es robusta:
  ```python
  except Exception as exc:
      record_retrieval_fallback("sparse")
      # log warning y degradar a dense-only
  ```
  Esto protege el SLA global ante fallas parciales (ej: FTS DB overload).

### 3. Tests y Documentación

- **Coverage**: El nuevo suite `test_pipeline_instrumentation` cubre los casos de éxito y de falla (fallback count).
- **Docs**: La sección "Queries PromQL Útiles" en el runbook facilita la adopción inmediata por parte de SREs.

## D) Riesgos y Mitigaciones

| Riesgo                | Impacto                    | Probabilidad | Mitigación                                                                                                 |
| :-------------------- | :------------------------- | :----------- | :--------------------------------------------------------------------------------------------------------- |
| **Volumen de Series** | Aumento marginal en TSDB   | Nula         | Son 4 histogramas x ~10 buckets = ~40 series nuevas. Despreciable.                                         |
| **Ruido en Logs**     | Warning flood si falla FTS | Baja         | El log está dentro del `try/except`. Si FTS cae masivamente, habrá warnings. Es el comportamiento deseado. |

## E) Recomendaciones

1.  **Dashboard**: Actualizar el JSON de Grafana (`ragcorp-api-performance.json`) para incluir una fila "Retrieval Breakdown" con estos 4 paneles.
2.  **Alertas**: Crear alerta `RetrievalFallbackRate > 5%` para detectar degradación de calidad de búsqueda (aunque no devuelva error 500).

## F) Veredicto

# ✅ GO

Instrumentación quirúrgica, necesaria para operar RAG en producción con confianza. Código limpio y defensivo.
