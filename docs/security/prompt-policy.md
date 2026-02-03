# Prompt policy y mitigación de inyección
Fuente de verdad: prompts y utilidades del backend.

## Policy contract
- Asset principal → `apps/backend/app/prompts/policy/secure_contract_es.md`.
- Loader → `apps/backend/app/infrastructure/prompts/loader.py`.

## Contexto con citas
- `ContextBuilder` compone contexto con `[S#]` y sección `FUENTES`.
- Evidencia: `apps/backend/app/application/context_builder.py`.

## Detector de inyección
- Detector heurístico → `apps/backend/app/application/prompt_injection_detector.py`.
- Modos de filtrado configurables → `rag_injection_filter_mode` en `apps/backend/app/crosscutting/config.py`.

## Métricas
- `rag_prompt_injection_detected_total` y `rag_policy_refusal_total` en `apps/backend/app/crosscutting/metrics.py`.
