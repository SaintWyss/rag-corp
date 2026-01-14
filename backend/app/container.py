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

from .config import get_settings
from .domain.repositories import DocumentRepository, ConversationRepository
from .domain.services import EmbeddingService, LLMService, TextChunkerService
from .infrastructure.cache import get_embedding_cache
from .infrastructure.repositories import (
    PostgresDocumentRepository,
    InMemoryConversationRepository,
)
from .infrastructure.services import (
    CachingEmbeddingService,
    FakeEmbeddingService,
    FakeLLMService,
    GoogleEmbeddingService,
    GoogleLLMService,
)
from .infrastructure.text import SimpleTextChunker
from .application.use_cases import (
    AnswerQueryUseCase,
    DeleteDocumentUseCase,
    GetDocumentUseCase,
    IngestDocumentUseCase,
    ListDocumentsUseCase,
    SearchChunksUseCase,
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


# R: AnswerQuery use case factory (creates new instance per request)
def get_answer_query_use_case() -> AnswerQueryUseCase:
    """
    R: Create AnswerQueryUseCase with injected dependencies.
    """
    return AnswerQueryUseCase(
        repository=get_document_repository(),
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
        embedding_service=get_embedding_service(),
    )


def get_list_documents_use_case() -> ListDocumentsUseCase:
    """R: Create ListDocumentsUseCase."""
    return ListDocumentsUseCase(repository=get_document_repository())


def get_get_document_use_case() -> GetDocumentUseCase:
    """R: Create GetDocumentUseCase."""
    return GetDocumentUseCase(repository=get_document_repository())


def get_delete_document_use_case() -> DeleteDocumentUseCase:
    """R: Create DeleteDocumentUseCase."""
    return DeleteDocumentUseCase(repository=get_document_repository())
