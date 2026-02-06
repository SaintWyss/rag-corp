# Auditoría Técnica: PR2 (`feat/rag-hybrid-rrf`)

## A) Resumen Ejecutivo

- **Estado**: ✅ **READY FOR MERGE**.
- **Propósito**: Implementa Hybrid Search (Vector + Full-Text) con fusión RRF, cubriendo una brecha crítica de retrieval para queries de palabras clave exactas.
- **Componentes**: Nueva columna `tsvector` generada, índice GIN, servicio `RankFusionService` (puro), y orquestación en casos de uso.
- **Seguridad**: Inmune a SQL Injection (parameterized queries). Mantiene scoping estricto por `workspace_id`.
- **Observabilidad**: Fallback transparente (si falla sparse, retorna dense) con logs de advertencia.

## B) Diff de Alto Nivel

| Archivo                                                             | Tipo        | Propósito                                                      |
| :------------------------------------------------------------------ | :---------- | :------------------------------------------------------------- |
| `apps/backend/alembic/versions/003_fts_tsvector_column.py`          | Migración   | Agrega col `tsv` (GENERATED) + Índice GIN ('spanish').         |
| `apps/backend/app/application/rank_fusion.py`                       | Servicio    | Implementación pura de Reciprocal Rank Fusion (k=60).          |
| `apps/backend/app/infrastructure/repositories/postgres/document.py` | Infra       | Implementa `find_chunks_full_text` con `websearch_to_tsquery`. |
| `apps/backend/app/application/usecases/chat/search_chunks.py`       | Application | Orquesta: Dense -> Sparse -> Fusion -> Rerank.                 |
| `apps/backend/tests/unit/application/test_rank_fusion.py`           | Test        | Unit tests exhaustivos para el algoritmo RRF.                  |
| `apps/backend/tests/unit/application/test_hybrid_search.py`         | Test        | Integration tests de los use cases (flags, fallback).          |

## C) Evaluación Técnica

### 1. Retrieval & RRF

- **Correctitud**: La fórmula RRF implementada (`1.0 / (k + rank)`) es correcta según el paper de Cormack.
- **Deduplicación**: Maneja correctamente la identidad del chunk usando `chunk_id` (UUID) o fallback a `doc_id:index`.
- **Pipeline**: El orden es correcto: Retrieval (Dense | Hybrid) -> Fusion -> Reranking -> Security Filter.

### 2. Base de Datos (Postgres/pgvector)

- **Full-Text Search**:
  - Usa `websearch_to_tsquery('spanish', ...)` lo cual es robusto para input de usuario (soporta quotes, `-negation`).
  - Columna `GENERATED ALWAYS`: Excelente decisión. Evita desincronización entre `content` y `tsv`.
  - Índice `GIN`: Esencial para performance.
- **Seguridad SQL**: Todos los inputs están parametrizados (`%s`). No hay interpolación de strings.

### 3. Observabilidad & Fallback

- **Graceful Degradation**: El código captura excepciones en la búsqueda sparse y loguea un WARNING, permitiendo que la búsqueda dense continúe. Esto es vital para la estabilidad.
- **Logging**: Se registran eventos clave (counts, errores) con `workspace_id` como contexto.

## D) Matriz de Riesgos

| Riesgo                             | Impacto                         | Probabilidad | Mitigación Propuesta                                                                                                           |
| :--------------------------------- | :------------------------------ | :----------- | :----------------------------------------------------------------------------------------------------------------------------- |
| **Idioma Hardcodeado ('spanish')** | Medio (Recall en otros idiomas) | Alta         | El stemmer 'spanish' funciona aceptablemente para inglés, pero no es ideal. A futuro: parametrizar idioma por workspace.       |
| **Performance (top_k expansion)**  | Bajo                            | Baja         | RRF requiere traer `top_k` de dos fuentes. Si `top_k` es alto (>100), la latencia aumenta. El límite `_MAX_TOP_K` mitiga esto. |
| **Escalabilidad GIN**              | Medio (Write throughput)        | Baja         | GIN es más lento en inserts que B-Tree. Con el volumen actual (<1M chunks), es despreciable.                                   |

## E) Recomendaciones

1.  **Monitor Latency**: Vigilar el histograma de latencia de `find_chunks_full_text`. GIN puede ser lento con queries muy genéricos (stop words).
2.  **Configurar Idioma**: Considerar mover `'spanish'` a una constante de configuración o columna en Workspace para soporte multi-idioma real.
3.  **Test E2E**: Agregar un test end-to-end con un documento real (PDF) que contenga un término "raro" (ej: código de error) y verificar que Hybrid lo encuentre en top-1 mientras Dense quizás no.
4.  **Tuning k**: El valor `k=60` es estándar, pero podría beneficiarse de tuning basado en métricas reales de click-through rate si se implementa feedback loop.

## F) Veredicto

# ✅ GO

La implementación es sólida, segura y sigue las mejores prácticas de Clean Architecture. Los tests cubren los casos bordes críticos. Está listo para producción.
