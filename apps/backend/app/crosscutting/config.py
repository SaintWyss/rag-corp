# apps/backend/app/crosscutting/config.py
"""
===============================================================================
MÓDULO: Configuración de la aplicación (Settings)
===============================================================================

BUSINESS GOAL
-------------
Tener un “source of truth” de configuración runtime:
- Tipada
- Validada al inicio
- Con defaults seguros

PATRONES
--------
- Singleton (lru_cache) para settings
- Validación centralizada (Pydantic validators)
- Fail-fast en producción (se valida seguridad y dependencias)

-------------------------------------------------------------------------------
CRC (Component Card)
-------------------------------------------------------------------------------
Componente:
  Settings

Responsabilidades:
  - Parsear variables de entorno y validar constraints
  - Proveer límites y toggles de features (seguridad / performance / observabilidad)
  - Entregar helpers de parseo (ej: allowed_origins -> list)

Colaboradores:
  - app/api/main.py (CORS, middlewares)
  - app/container.py (inyección de dependencias)
  - app/interfaces/... (límites de request / defaults)
===============================================================================
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from uuid import UUID

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_VERSION_RE = re.compile(r"^v\d+$", re.IGNORECASE)


class Settings(BaseSettings):
    """
    Settings globales de la aplicación.

    Nota importante:
    - Esto NO es dominio. Es configuración y límites de infraestructura / API.
    """

    # -------------------------------------------------------------------------
    # Runtime / entorno
    # -------------------------------------------------------------------------
    app_env: str = "development"  # development | production
    service_name: str = "rag-corp-api"
    log_level: str = "INFO"
    log_json: bool = True

    # -------------------------------------------------------------------------
    # Dependencias externas
    # -------------------------------------------------------------------------
    database_url: str
    google_api_key: str = ""

    # -------------------------------------------------------------------------
    # Testing / modo fake
    # -------------------------------------------------------------------------
    fake_llm: bool = False
    fake_embeddings: bool = False

    # -------------------------------------------------------------------------
    # CORS
    # -------------------------------------------------------------------------
    allowed_origins: str = "http://localhost:3000"
    cors_allow_credentials: bool = False

    # -------------------------------------------------------------------------
    # Límites y seguridad de requests
    # -------------------------------------------------------------------------
    max_body_bytes: int = 10 * 1024 * 1024  # 10MB
    max_upload_bytes: int = 25 * 1024 * 1024  # 25MB

    # -------------------------------------------------------------------------
    # Límites de API
    # -------------------------------------------------------------------------
    max_top_k: int = 20
    max_ingest_chars: int = 100_000
    max_query_chars: int = 2_000
    max_title_chars: int = 200
    max_source_chars: int = 500

    # -------------------------------------------------------------------------
    # Chunking (texto)
    # -------------------------------------------------------------------------
    chunk_size: int = 900
    chunk_overlap: int = 120

    # -------------------------------------------------------------------------
    # Redis (cola/cache)
    # -------------------------------------------------------------------------
    redis_url: str = ""

    # -------------------------------------------------------------------------
    # API Keys / RBAC (protección de endpoints y métricas)
    # -------------------------------------------------------------------------
    api_keys_config: str = ""
    metrics_require_auth: bool = False

    # -------------------------------------------------------------------------
    # Rate limiting
    # -------------------------------------------------------------------------
    rate_limit_rps: float = 10.0
    rate_limit_burst: int = 20

    # -------------------------------------------------------------------------
    # JWT / cookies
    # -------------------------------------------------------------------------
    jwt_secret: str = "dev-secret"
    jwt_access_ttl_minutes: int = 30
    jwt_cookie_name: str = "access_token"
    jwt_cookie_secure: bool = False

    # -------------------------------------------------------------------------
    # S3/MinIO
    # -------------------------------------------------------------------------
    s3_endpoint_url: str = ""
    s3_bucket: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = ""

    # -------------------------------------------------------------------------
    # Database pool
    # -------------------------------------------------------------------------
    db_pool_min_size: int = 2
    db_pool_max_size: int = 10
    db_statement_timeout_ms: int = 30_000

    # -------------------------------------------------------------------------
    # Observabilidad
    # -------------------------------------------------------------------------
    otel_enabled: bool = False
    healthcheck_google_enabled: bool = True

    # -------------------------------------------------------------------------
    # Calidad RAG / comportamiento chat
    # -------------------------------------------------------------------------
    prompt_version: str = "v1"  # Debe ser del estilo vN para el loader de prompts
    max_context_chars: int = 12_000
    default_use_mmr: bool = False
    max_conversation_messages: int = 12

    rag_injection_filter_mode: str = "off"  # off | downrank | exclude
    rag_injection_risk_threshold: float = 0.6

    enable_query_rewrite: bool = False
    enable_rerank: bool = False
    rerank_candidate_multiplier: int = 5
    rerank_max_candidates: int = 200

    # -------------------------------------------------------------------------
    # Retrys (resiliencia)
    # -------------------------------------------------------------------------
    retry_max_attempts: int = 3
    retry_base_delay_seconds: float = 1.0
    retry_max_delay_seconds: float = 30.0

    # -------------------------------------------------------------------------
    # Seed de dev
    # -------------------------------------------------------------------------
    dev_seed_admin: bool = False
    dev_seed_admin_email: str = "admin@local"
    dev_seed_admin_password: str = "admin"
    dev_seed_admin_role: str = "admin"
    dev_seed_admin_force_reset: bool = False
    dev_seed_demo: bool = False

    # -------------------------------------------------------------------------
    # Validaciones campo a campo
    # -------------------------------------------------------------------------
    @field_validator("app_env")
    @classmethod
    def _validate_env(cls, v: str) -> str:
        env = (v or "").strip().lower()
        return env or "development"

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        lvl = (v or "INFO").strip().upper()
        return lvl

    @field_validator("chunk_size")
    @classmethod
    def _validate_chunk_size(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("chunk_size debe ser > 0")
        return v

    @field_validator("chunk_overlap")
    @classmethod
    def _validate_chunk_overlap(cls, v: int) -> int:
        if v < 0:
            raise ValueError("chunk_overlap debe ser >= 0")
        return v

    @field_validator("max_body_bytes", "max_upload_bytes")
    @classmethod
    def _validate_sizes(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("los tamaños máximos deben ser > 0")
        # Defensa: evitar valores absurdos por error de configuración
        if v > 500 * 1024 * 1024:  # 500MB
            raise ValueError("tamaño máximo demasiado alto (revisar configuración)")
        return v

    @field_validator("rate_limit_rps")
    @classmethod
    def _validate_rps(cls, v: float) -> float:
        if v < 0:
            raise ValueError("rate_limit_rps debe ser >= 0")
        return v

    @field_validator("rate_limit_burst")
    @classmethod
    def _validate_burst(cls, v: int) -> int:
        if v < 0:
            raise ValueError("rate_limit_burst debe ser >= 0")
        return v

    @field_validator("rag_injection_filter_mode")
    @classmethod
    def _validate_filter_mode(cls, v: str) -> str:
        mode = (v or "off").strip().lower()
        if mode not in {"off", "downrank", "exclude"}:
            raise ValueError("rag_injection_filter_mode debe ser: off|downrank|exclude")
        return mode

    @field_validator("rag_injection_risk_threshold")
    @classmethod
    def _validate_threshold(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError("rag_injection_risk_threshold debe estar entre 0 y 1")
        return v

    @field_validator("prompt_version")
    @classmethod
    def _validate_prompt_version(cls, v: str) -> str:
        pv = (v or "v1").strip()
        if not _VERSION_RE.match(pv):
            # No rompemos: el loader puede hacer fallback, pero avisamos temprano.
            raise ValueError("prompt_version debe tener formato vN (ej: v1, v2)")
        return pv

    @field_validator("rerank_candidate_multiplier")
    @classmethod
    def _validate_rerank_mult(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("rerank_candidate_multiplier debe ser > 0")
        return v

    @field_validator("rerank_max_candidates")
    @classmethod
    def _validate_rerank_max(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("rerank_max_candidates debe ser > 0")
        return v

    # -------------------------------------------------------------------------
    # Validaciones cruzadas (modelo)
    # -------------------------------------------------------------------------
    @model_validator(mode="after")
    def _validate_cross_fields(self) -> "Settings":
        # Overlap nunca debe ser >= size
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"chunk_overlap ({self.chunk_overlap}) debe ser < chunk_size ({self.chunk_size})"
            )

        # Validación de dependencias IA:
        # Si no hay API key, solo permitimos correr con fakes.
        if not self.google_api_key and not (self.fake_llm and self.fake_embeddings):
            raise ValueError(
                "GOOGLE_API_KEY es obligatorio salvo que FAKE_LLM=1 y FAKE_EMBEDDINGS=1"
            )

        # Producción: exigencias mínimas de seguridad.
        if self.is_production():
            self._validate_production_security()

        return self

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    def get_allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    def _validate_production_security(self) -> None:
        insecure = {"dev-secret", "changeme", "change-me", "password", "admin"}
        secret = (self.jwt_secret or "").strip()

        if not secret or secret.lower() in insecure:
            raise ValueError("JWT_SECRET debe ser fuerte y no default en producción")
        if len(secret) < 32:
            raise ValueError(
                "JWT_SECRET debe tener al menos 32 caracteres en producción"
            )

        if not self.jwt_cookie_secure:
            raise ValueError("JWT_COOKIE_SECURE debe ser true en producción")

        if not self.metrics_require_auth:
            raise ValueError("METRICS_REQUIRE_AUTH debe ser true en producción")

        # Para proteger /metrics, exigimos API_KEYS_CONFIG o RBAC_CONFIG (env).
        rbac_config = os.getenv("RBAC_CONFIG", "").strip()
        if not self.api_keys_config.strip() and not rbac_config:
            raise ValueError(
                "API_KEYS_CONFIG o RBAC_CONFIG es requerido en producción (protección de /metrics)"
            )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Singleton de Settings.

    Importante:
    - Se cachea para evitar re-parsing de env en cada request.
    """
    return Settings()
