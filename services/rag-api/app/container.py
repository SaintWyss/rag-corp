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

from .domain.repositories import DocumentRepository
from .domain.services import EmbeddingService, LLMService
from .infrastructure.repositories import PostgresDocumentRepository
from .infrastructure.services import GoogleEmbeddingService, GoogleLLMService
from .application.use_cases import AnswerQueryUseCase


# R: Repository factory (singleton)
@lru_cache
def get_document_repository() -> DocumentRepository:
    """
    R: Get singleton instance of document repository.
    
    Returns:
        PostgreSQL implementation of DocumentRepository
    """
    return PostgresDocumentRepository()


# R: Embedding service factory (singleton)
@lru_cache
def get_embedding_service() -> EmbeddingService:
    """
    R: Get singleton instance of embedding service.
    
    Returns:
        Google implementation of EmbeddingService
    """
    return GoogleEmbeddingService()


# R: LLM service factory (singleton)
@lru_cache
def get_llm_service() -> LLMService:
    """
    R: Get singleton instance of LLM service.
    
    Returns:
        Google implementation of LLMService
    """
    return GoogleLLMService()


# R: AnswerQuery use case factory (creates new instance per request)
def get_answer_query_use_case(
    repository: DocumentRepository = None,
    embedding_service: EmbeddingService = None,
    llm_service: LLMService = None
) -> AnswerQueryUseCase:
    """
    R: Create AnswerQueryUseCase with injected dependencies.
    
    Args:
        repository: Document repository (defaults to singleton)
        embedding_service: Embedding service (defaults to singleton)
        llm_service: LLM service (defaults to singleton)
    
    Returns:
        Configured AnswerQueryUseCase instance
    
    Notes:
        - Allows dependency injection for testing (pass mocks)
        - Uses singletons by default for production
    """
    return AnswerQueryUseCase(
        repository=repository or get_document_repository(),
        embedding_service=embedding_service or get_embedding_service(),
        llm_service=llm_service or get_llm_service()
    )
