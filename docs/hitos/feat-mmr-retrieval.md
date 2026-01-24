# Hito: feat/mmr-retrieval - MMR Retrieval + Prompt v2

## Objetivo
Exponer la funcionalidad de **Maximal Marginal Relevance (MMR)** en el flujo RAG para mejorar la diversidad de chunks recuperados, evitando redundancia. También se activa **prompt v2** como versión por defecto.

## Cambios realizados

### 1. Domain Layer
**Archivo:** `backend/app/domain/repositories.py`
- Agregado método `find_similar_chunks_mmr()` al Protocol `DocumentRepository`
- Parámetros: `embedding`, `top_k`, `fetch_k=20`, `lambda_mult=0.5`

### 2. Application Layer
**Archivo:** `backend/app/application/use_cases/answer_query.py`
- Campo `use_mmr: bool = False` agregado a `AnswerQueryInput`
- Lógica condicional en `execute()`:
  - Si `use_mmr=True`: usa `find_similar_chunks_mmr()`
  - Si `use_mmr=False`: usa `find_similar_chunks()` (comportamiento actual)
- Metadata del resultado incluye `use_mmr` para observabilidad

### 3. API Layer
**Archivo:** `backend/app/routes.py`
- Campo `use_mmr: bool = Field(default=False)` agregado a `QueryReq`
- El endpoint `/ask` pasa el parámetro al use case

### 4. Configuración
**Archivo:** `backend/app/config.py`
- `prompt_version` cambiado de `"v1"` a `"v2"`
- Agregado `default_use_mmr: bool = False` (preparación futura)

### 5. Tests
**Archivos:**
- `backend/tests/conftest.py`:
  - Mock `find_similar_chunks_mmr` agregado a `mock_repository`
  - Nuevo fixture `mock_context_builder` para aislar tests del context builder real
- `backend/tests/unit/test_answer_query_use_case.py`:
  - Nuevos tests: `test_execute_with_mmr_enabled`, `test_execute_without_mmr_uses_standard_search`
  - Todos los tests usan `mock_context_builder` para evitar dependencia de Settings

## Decisiones técnicas

1. **MMR opcional (opt-in)**: Se mantiene el comportamiento por defecto sin MMR para no impactar performance en queries existentes
2. **fetch_k = top_k × 4**: Se buscan 4x más candidatos para tener mejor diversidad en MMR
3. **lambda_mult = 0.5**: Balance equilibrado entre relevancia y diversidad
4. **Infraestructura existente**: El repositorio ya tenía `find_similar_chunks_mmr()` implementado; solo se expuso a través de la arquitectura limpia

## Uso

```bash
# Request con MMR habilitado
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "...", "use_mmr": true}'
```

## Validación

```bash
# Ejecutar tests unitarios
cd backend
pytest tests/unit/test_answer_query_use_case.py -v

# Verificar todos los tests
pytest tests/unit/ -v

# Resultado esperado: 262 passed
```

## Checklist
- [x] Tests unitarios pasan (262 tests)
- [x] Cobertura > 70% (94.94%)
- [x] No breaking changes (use_mmr=False por defecto)
- [x] Protocol actualizado con nuevo método
- [x] Metadata incluye use_mmr para observabilidad
