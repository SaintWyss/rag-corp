"""
Name: Application Configuration (Settings)

Responsibilities:
  - Centralized, typed configuration using pydantic-settings
  - Validate environment variables at startup
  - Provide defaults that match current behavior

Collaborators:
  - main.py: reads settings for CORS and startup validation
  - container.py: reads settings for chunker configuration
  - routes.py: reads settings for request validation limits

Constraints:
  - Lives in API/infrastructure layer, NOT in domain/application
  - No business logic — pure configuration

Notes:
  - Uses pydantic-settings for env parsing and validation
  - Singleton via lru_cache for performance
  - All limits configurable for different environments
"""

from functools import lru_cache
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Attributes:
        database_url: PostgreSQL connection string
        google_api_key: Google Gemini API key
        allowed_origins: Comma-separated CORS origins
        chunk_size: Characters per chunk (default: 900)
        chunk_overlap: Overlap between chunks (default: 120)
        max_top_k: Maximum top_k for queries (default: 20)
        max_ingest_chars: Maximum text length for ingestion (default: 100_000)
        max_query_chars: Maximum query length (default: 2_000)
        max_title_chars: Maximum title length (default: 200)
        max_source_chars: Maximum source length (default: 500)
        otel_enabled: Enable OpenTelemetry tracing (default: False)
        api_keys_config: JSON with API keys and scopes
        rate_limit_rps: Requests per second (default: 10)
        rate_limit_burst: Max burst tokens (default: 20)
        max_body_bytes: Max request body size (default: 10MB)
        metrics_require_auth: Require auth for /metrics (default: False)
        cors_allow_credentials: Allow cookies cross-origin (default: False)
        max_conversation_messages: Max chat history messages (default: 12)
        jwt_secret: Secret for signing JWT access tokens
        jwt_access_ttl_minutes: Access token TTL in minutes
        jwt_cookie_name: Cookie name for access token
        jwt_cookie_secure: Set Secure on auth cookies
    """

    # Required (no defaults)
    database_url: str
    google_api_key: str = ""

    # CORS configuration
    allowed_origins: str = "http://localhost:3000"

    # Chunking configuration (defaults match current behavior)
    chunk_size: int = 900
    chunk_overlap: int = 120

    # API limits (defaults match current implicit behavior)
    max_top_k: int = 20
    max_ingest_chars: int = 100_000
    max_query_chars: int = 2_000
    max_title_chars: int = 200
    max_source_chars: int = 500

    # Observability
    otel_enabled: bool = False

    # Testing/CI
    fake_llm: bool = False
    fake_embeddings: bool = False

    # Security - API Keys (JSON: {"key": ["scope1", "scope2"], ...})
    api_keys_config: str = ""

    # Security - Rate Limiting
    rate_limit_rps: float = 10.0
    rate_limit_burst: int = 20

    # Security - Hardening
    max_body_bytes: int = 10 * 1024 * 1024  # 10MB
    metrics_require_auth: bool = False
    cors_allow_credentials: bool = False

    # Security - JWT Auth
    jwt_secret: str = "dev-secret"
    jwt_access_ttl_minutes: int = 30
    jwt_cookie_name: str = "access_token"
    jwt_cookie_secure: bool = False

    # Database - Connection Pool
    db_pool_min_size: int = 2
    db_pool_max_size: int = 10
    db_statement_timeout_ms: int = 30000  # 30 seconds

    # RAG Quality
    prompt_version: str = "v2"  # R: v2 includes better grounding and injection protection
    max_context_chars: int = 12000
    default_use_mmr: bool = False  # R: MMR for diverse retrieval (default off for perf)
    max_conversation_messages: int = 12

    # Retry/Resilience
    retry_max_attempts: int = 3
    retry_base_delay_seconds: float = 1.0
    retry_max_delay_seconds: float = 30.0

    # Health Check Configuration
    healthcheck_google_enabled: bool = True  # Include Google API in full health check

    @field_validator("chunk_size")
    @classmethod
    def chunk_size_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("chunk_size must be greater than 0")
        return v

    @field_validator("chunk_overlap")
    @classmethod
    def chunk_overlap_must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("chunk_overlap must be >= 0")
        return v

    def validate_chunk_params(self) -> None:
        """
        Cross-field validation: overlap must be less than chunk_size.
        Called explicitly after instantiation.
        """
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"chunk_overlap ({self.chunk_overlap}) must be less than "
                f"chunk_size ({self.chunk_size})"
            )

    def get_allowed_origins_list(self) -> list[str]:
        """Parse comma-separated origins into a list."""
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]

    @model_validator(mode="after")
    def validate_ai_requirements(self):
        if not self.google_api_key and not (
            self.fake_llm and self.fake_embeddings
        ):
            raise ValueError(
                "GOOGLE_API_KEY is required unless FAKE_LLM=1 and FAKE_EMBEDDINGS=1"
            )
        return self

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore unknown env vars


@lru_cache
def get_settings() -> Settings:
    """
    Get singleton Settings instance.

    Raises:
        ValidationError: If required env vars are missing or invalid
    """
    settings = Settings()
    settings.validate_chunk_params()
    return settings
