# ADR-010: Prompt policy e inyección (estado actual)

Date: 2026-01-29

## Contexto
- El backend usa prompts versionados y un contexto con citas (RAG).
- Se requiere detección/mitigación de prompt-injection en texto recuperado.

## Decisión (evidencia)
1) **Policy contract central**
- Archivo: `apps/backend/app/prompts/policy/secure_contract_es.md`.
- Loader: `apps/backend/app/infrastructure/prompts/loader.py`.

2) **Contexto con citas estables**
- `ContextBuilder` compone contexto con delimitadores `[S#]` y sección `FUENTES`.
- Evidencia: `apps/backend/app/application/context_builder.py` (`CHUNK_DELIMITER`, `SOURCES_HEADER`).

3) **Detector de prompt injection**
- Detector heurístico: `apps/backend/app/application/prompt_injection_detector.py`.
- Modos: `off`, `downrank`, `exclude` (ver `Mode` en el mismo archivo y `rag_injection_filter_mode` en `apps/backend/app/crosscutting/config.py`).

4) **Observabilidad**
- Métricas: `rag_prompt_injection_detected_total`, `rag_policy_refusal_total`, `rag_answer_without_sources_total` en `apps/backend/app/crosscutting/metrics.py`.

## TODO (no verificado)
- Scoping estricto por `workspace_id` a través de API/use cases/repositorios. Verificar en `apps/backend/app/interfaces/api/http/routers/` y `apps/backend/app/application/usecases/workspace/`.
