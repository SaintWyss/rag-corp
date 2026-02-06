# ADR-015: Offline RAG Evaluation Harness

## Estado

**Aceptado** (2026-02)

## Contexto

El pipeline RAG (dense retrieval, hybrid search, reranking) evoluciona con cada mejora. Sin una forma sistematica de medir la calidad de retrieval, es imposible:

1. Detectar regresiones cuando se cambian embeddings, chunking, o estrategias de retrieval.
2. Comparar alternativas (dense-only vs hybrid, con/sin reranking).
3. Establecer baselines cuantificables para decisiones de ingenieria.

### Opciones evaluadas

| Opcion                             | Pros                                       | Contras                                         |
| ---------------------------------- | ------------------------------------------ | ----------------------------------------------- |
| Sin evaluacion (status quo)        | Zero esfuerzo                              | Sin visibilidad de calidad, regresiones ocultas |
| Evaluacion manual ad-hoc           | Flexible                                   | No reproducible, no automatizable               |
| **Harness offline con golden set** | Reproducible, automatizable, sin costo API | Dataset estatico, no cubre edge cases dinamicos |
| Evaluacion online (A/B test)       | Mide impacto real en usuarios              | Requiere trafico, infraestructura de A/B        |

## Decision

Implementamos un **harness de evaluacion offline** con las siguientes caracteristicas:

### Dataset Golden

- **Corpus**: 15 documentos representativos (politicas, procesos, guias tecnicas).
- **Queries**: 30 consultas con juicios de relevancia binaria (`relevant_docs`).
- **Formato**: JSONL para facil extension y versionado.
- **Categorias**: factual, how-to, compliance.

### Metricas

- **MRR** (Mean Reciprocal Rank) — posicion del primer resultado relevante.
- **Recall@k** — fraccion de relevantes en los top-k.
- **Hit@1** — precision del primer resultado.
- **NDCG@k** — ganancia descontada normalizada (relevancia binaria).

Las funciones de metricas son **puras** (sin IO, sin estado) — testeables independientemente con 26 unit tests.

### Script CLI

`scripts/eval_rag.py` ejecuta el pipeline completo:

1. Carga corpus y queries.
2. Embeddings + indexacion in-memory (cosine similarity).
3. Retrieval top-k por query.
4. Calculo de metricas.
5. Exportacion de reporte JSON.

No requiere base de datos ni servicios externos — usa `FakeEmbeddingService` por defecto.

### CI

Workflow manual/automatico (`.github/workflows/eval.yml`):

- Non-blocking (informativo, no falla el pipeline).
- Sube reporte como artifact.
- Trigger automatico cuando cambian archivos de evaluacion.

## Consecuencias

### Positivas

- Cualquier cambio en retrieval puede validarse cuantitativamente.
- El harness corre en <2s con fake embeddings (smoke test).
- Con embeddings reales, produce metricas comparables entre versiones.
- Dataset versionado junto al codigo — reproducible.

### Negativas

- Dataset estatico de 30 queries no cubre todos los edge cases.
- Con fake embeddings, los scores son ~random (solo verifica que el pipeline ejecuta).
- Requiere mantenimiento del golden set conforme evoluciona el dominio.

### Mitigaciones

- Extender el dataset es trivial (agregar lineas JSONL).
- El script acepta `FAKE_EMBEDDINGS=0` para evaluacion con embeddings reales.
- Smoke tests verifican que la infraestructura de evaluacion funciona siempre.
