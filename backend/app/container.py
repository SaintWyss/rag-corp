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
  - application.use_cases: AnswerQueryUseCase
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
"""

from functools import lru_cache
import os

from .config import get_settings
from .domain.repositories import (
    DocumentRepository,
    ConversationRepository,
    AuditEventRepository,
    WorkspaceRepository,
    WorkspaceAclRepository,
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
from .infrastructure.repositories import (
    PostgresDocumentRepository,
    PostgresAuditEventRepository,
    PostgresWorkspaceRepository,
    PostgresWorkspaceAclRepository,
    InMemoryConversationRepository,
    InMemoryWorkspaceRepository,
    InMemoryWorkspaceAclRepository,
)
from .infrastructure.services import (
    CachingEmbeddingService,
    FakeEmbeddingService,
    FakeLLMService,
    GoogleEmbeddingService,
    GoogleLLMService,
)
from .infrastructure.parsers import SimpleDocumentTextExtractor
from .infrastructure.queue import RQDocumentProcessingQueue
from .infrastructure.text import SimpleTextChunker
from .infrastructure.storage import S3FileStorageAdapter, S3Config
from .application.use_cases import (
    AnswerQueryUseCase,
    DeleteDocumentUseCase,
    GetDocumentUseCase,
    GetWorkspaceUseCase,
    IngestDocumentUseCase,
    ListDocumentsUseCase,
    ListWorkspacesUseCase,
    ReprocessDocumentUseCase,
    SearchChunksUseCase,
    UploadDocumentUseCase,
    CreateWorkspaceUseCase,
    ArchiveWorkspaceUseCase,
    UpdateWorkspaceUseCase,
    PublishWorkspaceUseCase,
    ShareWorkspaceUseCase,
)


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


# R: Text chunker factory (singleton)
@lru_cache
def get_text_chunker() -> TextChunkerService:
    """
    R: Get singleton instance of text chunker.

    Reads chunk_size and chunk_overlap from Settings.

    Returns:
        SimpleTextChunker implementation with configured params
    """
    settings = get_settings()
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


# R: Document processing queue factory (singleton)
@lru_cache
def get_document_queue() -> DocumentProcessingQueue | None:
    """R: Get queue for background document processing if configured."""
    settings = get_settings()
    if not settings.redis_url:
        return None
    return RQDocumentProcessingQueue(
        redis_url=settings.redis_url,
        retry_max_attempts=settings.retry_max_attempts,
    )

# R: AnswerQuery use case factory (creates new instance per request)
def get_answer_query_use_case() -> AnswerQueryUseCase:
    """
    R: Create AnswerQueryUseCase with injected dependencies.
    """
    return AnswerQueryUseCase(
        repository=get_document_repository(),
        workspace_repository=get_workspace_repository(),
        acl_repository=get_workspace_acl_repository(),
        embedding_service=get_embedding_service(),
        llm_service=get_llm_service(),
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
    return SearchChunksUseCase(
        repository=get_document_repository(),
        workspace_repository=get_workspace_repository(),
        acl_repository=get_workspace_acl_repository(),
        embedding_service=get_embedding_service(),
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
