# ADR-003: Google GenAI como proveedor LLM/Embeddings

## Estado
**Aceptado**

## Contexto
El backend necesita:
- Embeddings para búsqueda semántica.
- Generación de respuestas (LLM) para RAG.

## Decisión
Se usa Google GenAI como proveedor en infraestructura.

## Implementación (evidencia)
- Embeddings: `apps/backend/app/infrastructure/services/google_embedding_service.py`.
- LLM: `apps/backend/app/infrastructure/services/llm/google_llm_service.py`.
- Configuración: `GOOGLE_API_KEY` en `apps/backend/app/crosscutting/config.py`.

## Detalles de modelo (evidencia)
- Embeddings default: `text-embedding-004` (`google_embedding_service.py`).
- LLM default: `gemini-1.5-flash` (`google_llm_service.py`).

## Consecuencias
No verificado (ver TODO): costos, latencias y límites de rate. Revisar documentación del proveedor y contratos operativos.

## Referencias
- Código de servicios → `apps/backend/app/infrastructure/services/README.md`
- LLM → `apps/backend/app/infrastructure/services/llm/README.md`
