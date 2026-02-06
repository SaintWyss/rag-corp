# RAG Evaluation Harness

Herramienta offline para evaluar la calidad de retrieval del pipeline RAG.

---

## Objetivo

Medir de forma reproducible la calidad de retrieval usando un dataset dorado
(golden set) de consultas con juicios de relevancia. Esto permite:

- Detectar regresiones en la calidad de retrieval.
- Comparar embeddings / estrategias de retrieval.
- Establecer baselines antes y despues de cambios.

---

## Metricas

| Metrica  | Significado                                                              |
| -------- | ------------------------------------------------------------------------ |
| MRR      | Mean Reciprocal Rank — promedio de 1/rank del primer resultado relevante |
| Recall@k | Fraccion de docs relevantes encontrados en los top-k resultados          |
| Hit@1    | Fraccion de queries donde el top-1 es relevante                          |
| NDCG@k   | Normalized Discounted Cumulative Gain (relevancia binaria)               |

---

## Dataset

Ubicacion: `apps/backend/eval/dataset/`

| Archivo                | Contenido                                  |
| ---------------------- | ------------------------------------------ |
| `corpus.jsonl`         | 15 documentos (politicas, procesos, guias) |
| `golden_queries.jsonl` | 30 queries con juicios de relevancia       |

### Formato corpus

```jsonl
{
  "doc_id": "d001",
  "title": "PTO Policy",
  "content": "..."
}
```

### Formato queries

```jsonl
{
  "query_id": "q001",
  "query": "...",
  "relevant_docs": [
    "d001"
  ],
  "category": "factual"
}
```

### Categorias

- `factual` — preguntas de hecho con respuesta directa
- `how-to` — preguntas de procedimiento
- `compliance` — preguntas regulatorias/normativas

---

## Uso

### Ejecucion local

```bash
cd apps/backend

# Con fake embeddings (default, sin API key)
python scripts/eval_rag.py

# Con embeddings reales (requiere GOOGLE_API_KEY)
FAKE_EMBEDDINGS=0 python scripts/eval_rag.py

# Opciones
python scripts/eval_rag.py --top-k 10                # custom k
python scripts/eval_rag.py --out report.json          # guardar reporte
python scripts/eval_rag.py --verbose                  # detalle por query
```

### Ejemplo de output

```
==================================================
  RAG Evaluation Report
  Model: fake-embedding-v1
  Corpus: 15 docs | Queries: 30
  top_k: 5
==================================================
           mrr: 0.1161
      recall@5: 0.3000
         hit@1: 0.0333
        ndcg@5: 0.1609
       elapsed: 0.85s
==================================================
```

**Nota:** Con fake embeddings los scores son bajos (~random) porque los
embeddings hash-based no capturan semantica. Los scores reales con
Google Embeddings son significativamente mayores.

---

## CI

El workflow `.github/workflows/eval.yml` ejecuta la evaluacion:

- **Trigger manual** (`workflow_dispatch`) — permite seleccionar `top_k`.
- **Trigger automatico** — cuando cambian archivos en `eval/` o el script.
- **Non-blocking** — no falla el pipeline si los scores son bajos.
- **Artifact** — sube `eval-report.json` para revision (30 dias).

---

## Arquitectura

```
apps/backend/
  eval/
    __init__.py
    metrics.py          # Funciones puras: MRR, Recall@k, Hit@1, NDCG@k
    dataset/
      corpus.jsonl      # Documentos del golden set
      golden_queries.jsonl  # Queries con relevancia
  scripts/
    eval_rag.py         # CLI de evaluacion
  tests/unit/eval/
    test_eval_metrics.py       # 26 tests de metricas
    test_eval_script_smoke.py  # 8 smoke tests del script
```

### Flujo

1. Cargar corpus y queries desde JSONL.
2. Embeddear cada documento y query con `FakeEmbeddingService` (o real).
3. Indexar chunks en un mini-indice vectorial in-memory.
4. Para cada query: buscar top-k por cosine similarity.
5. Deduplicar resultados por `doc_id`.
6. Calcular metricas contra los juicios de relevancia.
7. Exportar reporte JSON.

---

## Extender el dataset

Para agregar queries o documentos:

1. Editar `corpus.jsonl` (agregar linea JSONL con nuevo doc).
2. Editar `golden_queries.jsonl` (agregar query con `relevant_docs`).
3. Correr `python scripts/eval_rag.py` para verificar.
4. Actualizar smoke test counts si cambia el total.

---

## Tests

```bash
# Solo metrics (26 tests, <1s)
pytest tests/unit/eval/test_eval_metrics.py -v

# Solo smoke (8 tests, ~2s)
pytest tests/unit/eval/test_eval_script_smoke.py -v

# Todo junto
pytest tests/unit/eval/ -v
```
