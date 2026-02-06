# Auditoría Técnica: `feat/rag-eval-harness` (PR6)

## A) Resumen Ejecutivo

- **Estado**: ✅ **READY FOR MERGE**.
- **Propósito**: Marco de evaluación offline para calidad de retrieval (MRR, NDCG, Recall). Permite medir regresiones con datasets dorados.
- **Componentes**: Script de evaluación standalone, dataset inicial, métricas puras, y workflow de CI (non-blocking).
- **Reproducibilidad**: Usa `InMemoryVectorIndex` y `FakeEmbeddingService` por defecto para ejecuciones determinísticas en cualquier entorno.
- **Docs**: Excelente documentación en `docs/quality/rag-evaluation.md`.

## B) Tabla de Cambios

| Archivo                             | Tipo   | Propósito                                                                 |
| :---------------------------------- | :----- | :------------------------------------------------------------------------ |
| `apps/backend/scripts/eval_rag.py`  | Script | Ejecutor. Carga datos, indexa en memoria, corre queries y reporta JSON.   |
| `apps/backend/eval/metrics.py`      | Logic  | Implementación pura de métricas estándar IR (Hit@1, MRR, Recall, NDCG).   |
| `apps/backend/eval/dataset/*.jsonl` | Data   | Golden dataset inicial (15 docs, 30 queries). Formato JSONL.              |
| `.github/workflows/eval.yml`        | CI     | Workflow `workflow_dispatch` y `push` a paths eval. Genera artifact JSON. |
| `apps/backend/tests/unit/eval/`     | Tests  | Coverage unitario de métricas y smoke tests del script.                   |

## C) Evaluación Técnica

### 1. Dataset y Métricas

- **Dataset**: JSONL estable y versionado. Incluye `category` ("factual", "how-to") para análisis granular.
- **Métricas**: Correctamente implementadas según definiciones IR estándar. NDCG usa relevancia binaria, adecuado para el esquema actual.
- **Tests**: Coverage completo de métricas, incluyendo casos borde (k=0, empty lists).

### 2. Script y Reproducibilidad

- **Aislamiento**: El script no depende de DB ni Docker. Corre con `python eval_rag.py` usando deps del backend (`sys.path` hack).
- **Chunking**: Implementa su propio `_chunk_text` simple. Esto **difiere** del `SemanticChunker` de producción, lo cual introduce un sesgo (la evaluación no es 100% fiel a la app real).

### 3. CI/CD

- **Non-blocking**: Correcto. Falla del eval no rompe el build.
- **Artifacts**: Sube el reporte JSON (`retention-days: 30`), útil para comparar runs.

## D) Matriz de Riesgos

| Riesgo                | Impacto                       | Probabilidad | Mitigación                                                                                       |
| :-------------------- | :---------------------------- | :----------- | :----------------------------------------------------------------------------------------------- |
| **Drift de Chunking** | Evalúa lógica distinta a prod | Alta         | El script usa split simple vs SemanticChunker. **Recomendación**: Importar chunker real.         |
| **Scores "Fake"**     | Falsos positivos              | Media        | CI usa FakeEmbeddings (random). Solo prueba que el script corre, no la calidad. Docs lo aclaran. |

## E) Recomendaciones

1.  **Unificar Chunker**: Reemplazar `_chunk_text` por `app.infrastructure.text.semantic_chunker` para fidelidad real.
2.  **Nightly Real**: Configurar job nocturno con `FAKE_EMBEDDINGS=0` y secrets reales.
3.  **Thresholds**: A futuro, fallar si Recall cae X% (solo en nightly).

## F) Veredicto

# ✅ GO

Adición de alto valor para madurez de ingeniería. El harness es portable, rápido y bien documentado. La divergencia de chunking es aceptable en fase inicial pero debe corregirse.
