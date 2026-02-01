"""
Name: Dependency Injection Container

Responsibilities:
  - Wire up dependencies for the application
  - Provide factory functions for use cases
  - Manage singleton instances of repositories and services
  - Enable dependency injection in FastAPI endpoints

Collaborators:
  - infrastructure.repositories: PostgresDocumentRepository
  - infrastructure.services: GoogleEmbeddingService, GoogleLLMService
  - application.usecases: AnswerQueryUseCase
  - FastAPI Depends(): Dependency injection mechanism

Constraints:
  - Manual DI (no library like dependency-injector)
  - Singletons via functools.lru_cache
  - Environment-based configuration

Notes:
  - This is the composition root (where dependencies are wired)
  - Use cases don't know about concrete implementations
  - Easy to swap implementations (e.g., OpenAI instead of Google)
  - Testable (can inject mocks)

CRC (Component Card):
  Component: container
  Responsibilities:
    - Construir dependencias y casos de uso con DI manual
    - Centralizar configuración runtime (Settings)
  Collaborators:
    - application.usecases
    - infrastructure.repositories/services
    - crosscutting.config
"""

import os
from functools import lru_cache

from redis import Redis

from .application import RerankerMode, get_chunk_reranker, get_query_rewriter
from .application.usecases import (
    AnswerQueryUseCase,
    ArchiveWorkspaceUseCase,
    CreateWorkspaceUseCase,
    DeleteDocumentUseCase,
    GetDocumentUseCase,
    GetWorkspaceUseCase,
    IngestDocumentUseCase,
    ListDocumentsUseCase,
    ListWorkspacesUseCase,
    PublishWorkspaceUseCase,
    ReprocessDocumentUseCase,
    SearchChunksUseCase,
    ShareWorkspaceUseCase,
    UpdateWorkspaceUseCase,
    UploadDocumentUseCase,
)
from .application.usecases.chat import AnswerQueryWithHistoryUseCase
from .crosscutting.config import get_settings
from .domain.repositories import (
    AuditEventRepository,
    ConversationRepository,
    DocumentRepository,
    WorkspaceAclRepository,
    WorkspaceRepository,
)
from .domain.services import (
    DocumentProcessingQueue,
    DocumentTextExtractor,
    EmbeddingService,
    FileStoragePort,
    LLMService,
    TextChunkerService,
)
from .infrastructure.cache import get_embedding_cache
from .infrastructure.parsers import SimpleDocumentTextExtractor
from .infrastructure.queue import RQDocumentProcessingQueue, RQQueueConfig
from .infrastructure.repositories import (
    InMemoryConversationRepository,
    InMemoryWorkspaceAclRepository,
    InMemoryWorkspaceRepository,
    PostgresAuditEventRepository,
    PostgresDocumentRepository,
    PostgresWorkspaceAclRepository,
    PostgresWorkspaceRepository,
)
from .infrastructure.services import (
    CachingEmbeddingService,
    FakeEmbeddingService,
    FakeLLMService,
    GoogleEmbeddingService,
    GoogleLLMService,
)
from .infrastructure.storage import S3Config, S3FileStorageAdapter
from .infrastructure.text import SimpleTextChunker


# R: Repository factory (singleton)
@lru_cache
def get_document_repository() -> DocumentRepository:
    """
    R: Get singleton instance of document repository.

    Returns:
        PostgreSQL implementation of DocumentRepository
    """
    return PostgresDocumentRepository()


@lru_cache
def get_conversation_repository() -> ConversationRepository:
    """
    R: Get singleton instance of conversation repository.

    Returns:
        In-memory implementation of ConversationRepository
    """
    settings = get_settings()
    return InMemoryConversationRepository(
        max_messages=settings.max_conversation_messages
    )


@lru_cache
def get_workspace_repository() -> WorkspaceRepository:
    """R: Get singleton instance of workspace repository."""
    if os.getenv("APP_ENV", "development").strip().lower() in {"test", "testing"}:
        return InMemoryWorkspaceRepository()
    return PostgresWorkspaceRepository()


@lru_cache
def get_workspace_acl_repository() -> WorkspaceAclRepository:
    """R: Get singleton instance of workspace ACL repository."""
    if os.getenv("APP_ENV", "development").strip().lower() in {"test", "testing"}:
        return InMemoryWorkspaceAclRepository()
    return PostgresWorkspaceAclRepository()


@lru_cache
def get_audit_repository() -> AuditEventRepository:
    """R: Get singleton instance of audit repository."""
    return PostgresAuditEventRepository()


# R: Embedding service factory (singleton)
@lru_cache
def get_embedding_service() -> EmbeddingService:
    """
    R: Get singleton instance of embedding service.

    Returns:
        Google or Fake implementation of EmbeddingService
    """
    settings = get_settings()
    provider: EmbeddingService
    if settings.fake_embeddings:
        provider = FakeEmbeddingService()
    else:
        provider = GoogleEmbeddingService()
    return CachingEmbeddingService(
        provider=provider,
        cache=get_embedding_cache(),
    )


# R: LLM service factory (singleton)
@lru_cache
def get_llm_service() -> LLMService:
    """
    R: Get singleton instance of LLM service.

    Returns:
        Google or Fake implementation of LLMService
    """
    settings = get_settings()
    if settings.fake_llm:
        return FakeLLMService()
    return GoogleLLMService()


@lru_cache
def get_query_rewriter_service():
    """
    R: Get QueryRewriter instance if feature flag is enabled.
    """
    settings = get_settings()
    if not settings.enable_query_rewrite:
        return None
    return get_query_rewriter(
        get_llm_service(),
        enabled=settings.enable_query_rewrite,
    )


@lru_cache
def get_chunk_reranker_service():
    """
    R: Get ChunkReranker instance if feature flag is enabled.
    """
    settings = get_settings()
    if not settings.enable_rerank:
        return None
    return get_chunk_reranker(
        get_llm_service(),
        mode=RerankerMode.HEURISTIC,
    )


# R: Text chunker factory (singleton)
@lru_cache
def get_text_chunker() -> TextChunkerService:
    """
    R: Get singleton instance of text chunker.

    Mode selection via env TEXT_CHUNKER_MODE:
      - 'simple' (default): Recursive character splitting
      - 'structured': Markdown/Structure aware splitting

    Returns:
        TextChunkerService implementation
    """
    import os

    from .crosscutting.config import get_settings
    from .infrastructure.text import SimpleTextChunker, StructuredTextChunker

    settings = get_settings()
    mode = os.getenv("TEXT_CHUNKER_MODE", "simple").strip().lower()

    if mode == "structured":
        # R: Structured chunker preserves markdown headers and code blocks
        return StructuredTextChunker(
            max_chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap,
        )

    # Default fallback
    return SimpleTextChunker(
        chunk_size=settings.chunk_size,
        overlap=settings.chunk_overlap,
    )


@lru_cache
def get_file_storage() -> FileStoragePort | None:
    """
    R: Get file storage adapter if configured.

    Returns:
        S3FileStorageAdapter or None when storage is disabled.
    """
    settings = get_settings()
    if not settings.s3_bucket:
        return None
    if not settings.s3_access_key or not settings.s3_secret_key:
        return None

    config = S3Config(
        bucket=settings.s3_bucket,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        region=settings.s3_region or None,
        endpoint_url=settings.s3_endpoint_url or None,
    )
    return S3FileStorageAdapter(config)


# R: Document text extractor factory (singleton)
@lru_cache
def get_document_text_extractor() -> DocumentTextExtractor:
    """R: Get singleton instance of document text extractor."""
    return SimpleDocumentTextExtractor()


# R: Redis client factory (singleton)
@lru_cache
def get_redis_client() -> Redis | None:
    """R: Get singleton Redis client for infrastructure adapters.

    Nota:
      - Evita múltiples pools de conexiones en el proceso del API.
      - Si no hay redis_url configurado, retorna None.
    """
    settings = get_settings()
    redis_url = (settings.redis_url or os.getenv("REDIS_URL", "")).strip()
    if not redis_url:
        return None
    return Redis.from_url(redis_url)


# R: Document processing queue factory (singleton)
@lru_cache
def get_document_queue() -> DocumentProcessingQueue | None:
    """R: Get queue for background document processing if configured."""
    settings = get_settings()
    redis = get_redis_client()
    if redis is None:
        return None

    # Fuente única de nombre de cola: el worker también usa DOCUMENT_QUEUE_NAME.
    queue_name = os.getenv("DOCUMENT_QUEUE_NAME", "documents").strip() or "documents"

    config = RQQueueConfig(
        queue_name=queue_name,
        retry_max_attempts=settings.retry_max_attempts,
    )
    return RQDocumentProcessingQueue(redis=redis, config=config)


# R: AnswerQuery use case factory (creates new instance per request)
def get_answer_query_use_case() -> AnswerQueryUseCase:
    """
    R: Create AnswerQueryUseCase with injected dependencies.
    """
    settings = get_settings()
    return AnswerQueryUseCase(
        repository=get_document_repository(),
        workspace_repository=get_workspace_repository(),
        acl_repository=get_workspace_acl_repository(),
        embedding_service=get_embedding_service(),
        llm_service=get_llm_service(),
        injection_filter_mode=settings.rag_injection_filter_mode,
        injection_risk_threshold=settings.rag_injection_risk_threshold,
        reranker=get_chunk_reranker_service(),
        enable_rerank=settings.enable_rerank,
        rerank_candidate_multiplier=settings.rerank_candidate_multiplier,
        rerank_max_candidates=settings.rerank_max_candidates,
    )


def get_answer_query_with_history_use_case() -> AnswerQueryWithHistoryUseCase:
    """
    R: Create AnswerQueryWithHistoryUseCase with injected dependencies.
    """
    return AnswerQueryWithHistoryUseCase(
        conversation_repository=get_conversation_repository(),
        answer_query_use_case=get_answer_query_use_case(),
        query_rewriter=get_query_rewriter_service(),
    )


# R: IngestDocument use case factory
def get_ingest_document_use_case() -> IngestDocumentUseCase:
    """
    R: Create IngestDocumentUseCase with injected dependencies.
    """
    return IngestDocumentUseCase(
        repository=get_document_repository(),
        workspace_repository=get_workspace_repository(),
        embedding_service=get_embedding_service(),
        chunker=get_text_chunker(),
    )


# R: SearchChunks use case factory
def get_search_chunks_use_case() -> SearchChunksUseCase:
    """
    R: Create SearchChunksUseCase with injected dependencies.
    """
    settings = get_settings()
    return SearchChunksUseCase(
        repository=get_document_repository(),
        workspace_repository=get_workspace_repository(),
        acl_repository=get_workspace_acl_repository(),
        embedding_service=get_embedding_service(),
        injection_filter_mode=settings.rag_injection_filter_mode,
        injection_risk_threshold=settings.rag_injection_risk_threshold,
        reranker=get_chunk_reranker_service(),
        enable_rerank=settings.enable_rerank,
        rerank_candidate_multiplier=settings.rerank_candidate_multiplier,
        rerank_max_candidates=settings.rerank_max_candidates,
    )


def get_list_documents_use_case() -> ListDocumentsUseCase:
    """R: Create ListDocumentsUseCase."""
    return ListDocumentsUseCase(
        repository=get_document_repository(),
        workspace_repository=get_workspace_repository(),
        acl_repository=get_workspace_acl_repository(),
    )


def get_list_workspaces_use_case() -> ListWorkspacesUseCase:
    """R: Create ListWorkspacesUseCase."""
    return ListWorkspacesUseCase(
        repository=get_workspace_repository(),
        acl_repository=get_workspace_acl_repository(),
    )


def get_get_document_use_case() -> GetDocumentUseCase:
    """R: Create GetDocumentUseCase."""
    return GetDocumentUseCase(
        repository=get_document_repository(),
        workspace_repository=get_workspace_repository(),
        acl_repository=get_workspace_acl_repository(),
    )


def get_get_workspace_use_case() -> GetWorkspaceUseCase:
    """R: Create GetWorkspaceUseCase."""
    return GetWorkspaceUseCase(
        repository=get_workspace_repository(),
        acl_repository=get_workspace_acl_repository(),
    )


def get_delete_document_use_case() -> DeleteDocumentUseCase:
    """R: Create DeleteDocumentUseCase."""
    return DeleteDocumentUseCase(
        repository=get_document_repository(),
        workspace_repository=get_workspace_repository(),
    )


def get_upload_document_use_case() -> UploadDocumentUseCase:
    """R: Create UploadDocumentUseCase."""
    return UploadDocumentUseCase(
        repository=get_document_repository(),
        workspace_repository=get_workspace_repository(),
        storage=get_file_storage(),
        queue=get_document_queue(),
    )


def get_reprocess_document_use_case() -> ReprocessDocumentUseCase:
    """R: Create ReprocessDocumentUseCase."""
    return ReprocessDocumentUseCase(
        repository=get_document_repository(),
        workspace_repository=get_workspace_repository(),
        queue=get_document_queue(),
    )


def get_create_workspace_use_case() -> CreateWorkspaceUseCase:
    """R: Create CreateWorkspaceUseCase."""
    return CreateWorkspaceUseCase(repository=get_workspace_repository())


def get_archive_workspace_use_case() -> ArchiveWorkspaceUseCase:
    """R: Create ArchiveWorkspaceUseCase."""
    return ArchiveWorkspaceUseCase(
        repository=get_workspace_repository(),
        document_repository=get_document_repository(),
    )


def get_update_workspace_use_case() -> UpdateWorkspaceUseCase:
    """R: Create UpdateWorkspaceUseCase."""
    return UpdateWorkspaceUseCase(repository=get_workspace_repository())


def get_publish_workspace_use_case() -> PublishWorkspaceUseCase:
    """R: Create PublishWorkspaceUseCase."""
    return PublishWorkspaceUseCase(repository=get_workspace_repository())


def get_share_workspace_use_case() -> ShareWorkspaceUseCase:
    """R: Create ShareWorkspaceUseCase."""
    return ShareWorkspaceUseCase(
        repository=get_workspace_repository(),
        acl_repository=get_workspace_acl_repository(),
    )
