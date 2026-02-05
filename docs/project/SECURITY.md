<!--
===============================================================================
TARJETA CRC - docs/project/SECURITY.md
===============================================================================
Responsabilidades:
- Documentar las politicas de seguridad y fuentes de verdad.
- Centralizar referencias a autenticacion, RBAC, limites y secretos.

Colaboradores:
- docs/runbook/security-rotation.md
- apps/backend/app/*
- shared/contracts/openapi.json

Invariantes:
- No incluir secretos reales en el repositorio.
===============================================================================
-->
# Seguridad
Fuente de verdad: `apps/backend/app/` (config, identity, prompts, métricas).

## Autenticación y autorización
- API Keys (`X-API-Key`) → `apps/backend/app/identity/auth.py`.
- RBAC para API keys → `apps/backend/app/identity/rbac.py`.
- JWT para usuarios (roles `admin`/`employee`) → `apps/backend/app/identity/users.py` y `apps/backend/app/identity/auth_users.py`.
- Principal unificado (USER/SERVICE) → `apps/backend/app/identity/dual_auth.py`.

## Límites y validaciones
Fuente: `apps/backend/app/crosscutting/config.py`.
- `max_body_bytes` (body HTTP)
- `max_upload_bytes` (uploads)
- `max_query_chars`
- `max_ingest_chars`

## Prompt policy
- Prompt de policy (asset) → `apps/backend/app/prompts/policy/secure_contract_es.md`.
- Loader de prompts → `apps/backend/app/infrastructure/prompts/loader.py`.
- LLM real consume `PromptLoader` → `apps/backend/app/infrastructure/services/llm/google_llm_service.py`.

## Prompt injection (detección)
- Detector → `apps/backend/app/application/prompt_injection_detector.py`.
- Uso en ingesta → `apps/backend/app/application/usecases/ingestion/ingest_document.py` y `process_uploaded_document.py`.

## Métricas de seguridad
Definidas en `apps/backend/app/crosscutting/metrics.py`:
- `rag_policy_refusal_total`
- `rag_prompt_injection_detected_total`
- `rag_cross_scope_block_total`
- `rag_answer_without_sources_total`
- `rag_sources_returned_count`

## /metrics protegido
- Protección por API key/RBAC según `metrics_require_auth` → `apps/backend/app/crosscutting/config.py`.
- Dependencia en API → `apps/backend/app/identity/rbac.py` (`require_metrics_permission`).
- En worker → `apps/backend/app/worker/worker_server.py`.

## Secretos y rotación
- No se versionan secretos reales.
- Template K8s (no aplicar): `infra/k8s/base/secret.yaml`.
- ExternalSecrets (recomendado): `infra/k8s/externalsecrets/`.
- Runbook de rotación: `docs/runbook/security-rotation.md`.

Variables sensibles mínimas:
- `DATABASE_URL`
- `GOOGLE_API_KEY`
- `JWT_SECRET`
- `API_KEYS_CONFIG` o `RBAC_CONFIG`

## Tests relevantes
- Unit tests: `apps/backend/tests/unit/README.md`.
- Integration tests: `apps/backend/tests/integration/README.md`.

## Notas
- La fuente de verdad está en el código (`apps/backend/app/`) y en OpenAPI (`shared/contracts/openapi.json`).
