# Auditoría Técnica: PR1 (`feat/rag-hnsw-index`)

## A) Resumen Ejecutivo

- **Estado**: ✅ **READY FOR MERGE** (con nota menor sobre validación).
- **Propósito**: Migración de índice vectorial de IVFFlat a HNSW para mejorar recall y eliminar mantenimiento (`VACUUM`/`REINDEX`).
- **Cobertura**: Incluye Migración (Alembic), ADR de decisión y actualización de documentación de arquitectura.
- **Compatibilidad**: Transparente para la aplicación; no requiere cambios en código de consultas SQL.
- **Riesgo Técnico**: Bajo para el volumen actual (<100K registros). Procedimientos de rollback claros.

## B) Diff de Alto Nivel

| Archivo                                                         | Tipo          | Propósito                                                               |
| :-------------------------------------------------------------- | :------------ | :---------------------------------------------------------------------- |
| `apps/backend/alembic/versions/002_hnsw_vector_index.py`        | Migración     | Script DDL para drop IVFFlat / create HNSW.                             |
| `docs/architecture/adr/ADR-011-hnsw-vector-index.md`            | Documentación | Rationale de la decisión, parámetros y trade-offs.                      |
| `docs/reference/data/postgres-schema.md`                        | Documentación | Actualización de esquema de referencia para desarrolladores.            |
| `apps/backend/tests/integration/test_postgres_document_repo.py` | Test          | Validación indirecta. El test existente pasa, confirmando no-regresión. |
| `docs/architecture/adr/ADR-002-pgvector.md`                     | Documentación | Actualización menor (referencia cruzada).                               |

## C) Evaluación Técnica

### 1. Migración (`002_hnsw_vector_index.py`)

- **Correctitud**: Usa sintaxis correcta para pgvector (`USING hnsw`, `vector_cosine_ops`).
- **Idempotencia**: ✅ Usa `IF EXISTS` al borrar índices antiguos y nuevos antes de crear. Esto evita fallos en re-runs.
- **Downgrade**: ✅ Correctamente implementado. Borra HNSW y recrea IVFFlat.
  - _Nota_: Hardcodea `lists=100` para IVFFlat. Es un default razonable, pero técnicamente asume la configuración previa.
- **Locking**: La creación del índice NO es `CONCURRENTLY`.
  - _Evaluación_: Aceptable dado que Alembic corre en transacción DDL y el dataset es pequeño (<100K).

### 2. Tests (`test_postgres_document_repo.py`)

- **Funcionalidad**: Los tests de integración pasan (`find_similar_chunks`). Esto confirma que el operador `<=>` sigue funcionando.
- **Gap de Cobertura**: No hay un test que verifique explícitamente que el índice _existe_ o que el planner lo usa (`EXPLAIN`). Se confía en la ejecución exitosa de la migración.

### 3. Documentación (ADRs)

- **ADR-011**: Excelente nivel de detalle. Justifica la decisión basada en métricas ("<100K rows", "pgvector 0.5+"). Explica claramente cómo tunear `ef_search` en producción.

## D) Matriz de Riesgos

| Riesgo                 | Impacto                       | Probabilidad        | Mitigación Propuesta                                                                    |
| :--------------------- | :---------------------------- | :------------------ | :-------------------------------------------------------------------------------------- |
| **Bloqueo en Deploy**  | Medio (Downtime de escritura) | Baja (Volumen bajo) | Migración rápida (<5s estimado). Para futuro (>1M rows), requerirá `CONCURRENTLY`.      |
| **Aumento de Memoria** | Bajo                          | Alta                | HNSW consume más RAM que IVFFlat. Monitorear con query sugerida en ADR.                 |
| **Fallo de Build**     | Alto (Index corrupto)         | Baja                | `maintenance_work_mem` debe ser suficiente en Postgres.                                 |
| **Incompatibilidad**   | Alto (App Error)              | Nula                | El operador `<=>` es polimórfico en Postgres; la app no se entera del cambio de índice. |

## E) Recomendaciones

1.  **Post-Deploy Verification**: Ejecutar manualmente en PROD tras deploy:
    ```sql
    SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'chunks';
    ```
    Confirmar que aparece `hnsw`.
2.  **Monitor Memory**: Verificar el tamaño del índice tras la creación:
    ```sql
    SELECT pg_size_pretty(pg_relation_size('ix_chunks_embedding_hnsw'));
    ```
3.  **Tuning Futuro**: Si la latencia sube, recordar que HNSW permite ajustar `SET hnsw.ef_search` por sesión sin reindexar.
4.  **Downgrade Test**: En ambiente de staging, ejecutar `alembic downgrade 001` para verificar que la reversión a IVFFlat funciona sin errores.

## F) Veredicto

# ✅ GO

El cambio es sólido, bien documentado y técnicamente correcto. Los riesgos están acotados y documentados.
