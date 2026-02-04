# Configuración (Settings y variables de entorno)
Fuente de verdad: `apps/backend/app/crosscutting/config.py` (clase `Settings`).

## Cómo se carga
- `Settings` usa `pydantic_settings.BaseSettings` y lee `.env` (ver `SettingsConfigDict` en `apps/backend/app/crosscutting/config.py`).
- En producción, se aplican validaciones extra (seguridad JWT y métricas) dentro de `Settings._validate_production_security()`.

## Tabla de settings
Cada fila corresponde a un campo de `Settings` y su variable de entorno asociada.

| Campo (Settings) | Env var | Default |
| :-- | :-- | :-- |
| `app_env` | `APP_ENV` | `development` |
| `service_name` | `SERVICE_NAME` | `rag-corp-api` |
| `log_level` | `LOG_LEVEL` | `INFO` |
| `log_json` | `LOG_JSON` | `true` |
| `database_url` | `DATABASE_URL` | `(required)` |
| `google_api_key` | `GOOGLE_API_KEY` | `` |
| `fake_llm` | `FAKE_LLM` | `false` |
| `fake_embeddings` | `FAKE_EMBEDDINGS` | `false` |
| `allowed_origins` | `ALLOWED_ORIGINS` | `http://localhost:3000` |
| `cors_allow_credentials` | `CORS_ALLOW_CREDENTIALS` | `false` |
| `max_body_bytes` | `MAX_BODY_BYTES` | `10 * 1024 * 1024` |
| `max_upload_bytes` | `MAX_UPLOAD_BYTES` | `25 * 1024 * 1024` |
| `max_top_k` | `MAX_TOP_K` | `20` |
| `max_ingest_chars` | `MAX_INGEST_CHARS` | `100000` |
| `max_query_chars` | `MAX_QUERY_CHARS` | `2000` |
| `max_title_chars` | `MAX_TITLE_CHARS` | `200` |
| `max_source_chars` | `MAX_SOURCE_CHARS` | `500` |
| `chunk_size` | `CHUNK_SIZE` | `900` |
| `chunk_overlap` | `CHUNK_OVERLAP` | `120` |
| `redis_url` | `REDIS_URL` | `` |
| `api_keys_config` | `API_KEYS_CONFIG` | `` |
| `metrics_require_auth` | `METRICS_REQUIRE_AUTH` | `false` |
| `rate_limit_rps` | `RATE_LIMIT_RPS` | `10.0` |
| `rate_limit_burst` | `RATE_LIMIT_BURST` | `20` |
| `jwt_secret` | `JWT_SECRET` | `dev-secret` |
| `jwt_access_ttl_minutes` | `JWT_ACCESS_TTL_MINUTES` | `30` |
| `jwt_cookie_name` | `JWT_COOKIE_NAME` | `access_token` |
| `jwt_cookie_secure` | `JWT_COOKIE_SECURE` | `false` |
| `s3_endpoint_url` | `S3_ENDPOINT_URL` | `` |
| `s3_bucket` | `S3_BUCKET` | `` |
| `s3_access_key` | `S3_ACCESS_KEY` | `` |
| `s3_secret_key` | `S3_SECRET_KEY` | `` |
| `s3_region` | `S3_REGION` | `` |
| `db_pool_min_size` | `DB_POOL_MIN_SIZE` | `2` |
| `db_pool_max_size` | `DB_POOL_MAX_SIZE` | `10` |
| `db_statement_timeout_ms` | `DB_STATEMENT_TIMEOUT_MS` | `30000` |
| `otel_enabled` | `OTEL_ENABLED` | `false` |
| `healthcheck_google_enabled` | `HEALTHCHECK_GOOGLE_ENABLED` | `true` |
| `prompt_version` | `PROMPT_VERSION` | `v1` |
| `max_context_chars` | `MAX_CONTEXT_CHARS` | `12000` |
| `default_use_mmr` | `DEFAULT_USE_MMR` | `false` |
| `max_conversation_messages` | `MAX_CONVERSATION_MESSAGES` | `12` |
| `rag_injection_filter_mode` | `RAG_INJECTION_FILTER_MODE` | `off` |
| `rag_injection_risk_threshold` | `RAG_INJECTION_RISK_THRESHOLD` | `0.6` |
| `enable_query_rewrite` | `ENABLE_QUERY_REWRITE` | `false` |
| `enable_rerank` | `ENABLE_RERANK` | `false` |
| `rerank_candidate_multiplier` | `RERANK_CANDIDATE_MULTIPLIER` | `5` |
| `rerank_max_candidates` | `RERANK_MAX_CANDIDATES` | `200` |
| `retry_max_attempts` | `RETRY_MAX_ATTEMPTS` | `3` |
| `retry_base_delay_seconds` | `RETRY_BASE_DELAY_SECONDS` | `1.0` |
| `retry_max_delay_seconds` | `RETRY_MAX_DELAY_SECONDS` | `30.0` |
| `dev_seed_admin` | `DEV_SEED_ADMIN` | `false` |
| `dev_seed_admin_email` | `DEV_SEED_ADMIN_EMAIL` | `admin@local` |
| `dev_seed_admin_password` | `DEV_SEED_ADMIN_PASSWORD` | `admin` |
| `dev_seed_admin_role` | `DEV_SEED_ADMIN_ROLE` | `admin` |
| `dev_seed_admin_force_reset` | `DEV_SEED_ADMIN_FORCE_RESET` | `false` |
| `dev_seed_demo` | `DEV_SEED_DEMO` | `false` |

## Variables fuera de Settings
Estas variables no están en `Settings`, pero son leídas directamente por módulos del backend:
- `RBAC_CONFIG` (JSON) se lee en `apps/backend/app/identity/rbac.py` y se valida en producción desde `apps/backend/app/crosscutting/config.py`.
- `DOCUMENT_QUEUE_NAME` y `WORKER_HTTP_PORT` se leen en `apps/backend/app/worker/worker.py` para configurar el worker.

## Variables del frontend
Estas variables son leídas por el frontend:
- `RAG_BACKEND_URL` define el backend para `next.config.mjs` (rewrites).
- `JWT_COOKIE_DOMAIN` (opcional) permite borrar cookies con `Domain` desde el middleware.
