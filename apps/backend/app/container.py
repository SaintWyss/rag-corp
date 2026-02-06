"""
===============================================================================
TARJETA CRC — app/container.py (Composition Root / DI manual)
===============================================================================

Responsabilidades:
  - Componer dependencias (repositorios, servicios, adapters) siguiendo DIP.
  - Exponer factories para FastAPI (Depends) y para el worker.
  - Mantener singletons con caching (lru_cache) para recursos pesados.
  - Centralizar decisiones runtime basadas en Settings (config).

Colaboradores:
  - app.crosscutting.config.get_settings
  - app.domain.repositories.* (puertos)
  - app.domain.services.* (puertos)
  - app.infrastructure.* (implementaciones)
  - app.application.usecases.* (casos de uso)

Patrones aplicados:
  - Composition Root
  - Dependency Inversion (use cases dependen de puertos)
  - Lazy singletons con lru_cache

Notas:
  - Este archivo NO contiene lógica de negocio.
  - Este archivo NO debe depender de FastAPI (solo expone factories).
===============================================================================
"""

from __future__ import annotations

from functools import lru_cache

from redis import Redis

from .application import RerankerMode, get_chunk_reranker, get_query_rewriter
from .application.rank_fusion import RankFusionService
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

# =============================================================================
# Helpers internos
# =============================================================================


def _is_test_env() -> bool:
    """
    Determina si estamos en entorno de test.

    Regla:
      - app_env ∈ {"test", "testing", "ci"} => se favorecen in-memory adapters.
    """
    env = get_settings().app_env.strip().lower()
    return env in {"test", "testing", "ci"}


# =============================================================================
# Repositorios (singletons)
# =============================================================================


@lru_cache(maxsize=1)
def get_document_repository() -> DocumentRepository:
    """Devuelve el repositorio de documentos (Postgres)."""
    return PostgresDocumentRepository()


@lru_cache(maxsize=1)
def get_conversation_repository() -> ConversationRepository:
    """Repositorio de conversaciones (in-memory, acotado por Settings)."""
    settings = get_settings()
    return InMemoryConversationRepository(
        max_messages=settings.max_conversation_messages
    )


@lru_cache(maxsize=1)
def get_workspace_repository() -> WorkspaceRepository:
    """Repositorio de workspaces (in-memory en test; Postgres en runtime)."""
    if _is_test_env():
        return InMemoryWorkspaceRepository()
    return PostgresWorkspaceRepository()


@lru_cache(maxsize=1)
def get_workspace_acl_repository() -> WorkspaceAclRepository:
    """Repositorio de ACL de workspace (in-memory en test; Postgres en runtime)."""
    if _is_test_env():
        return InMemoryWorkspaceAclRepository()
    return PostgresWorkspaceAclRepository()


@lru_cache(maxsize=1)
def get_audit_repository() -> AuditEventRepository:
    """Repositorio de auditoría (Postgres)."""
    return PostgresAuditEventRepository()


# =============================================================================
# Servicios externos (singletons)
# =============================================================================


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """
    Servicio de embeddings con cache (DIP: CachingEmbeddingService envuelve proveedor).
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


@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    """Servicio LLM (fake en test/dev si está habilitado)."""
    settings = get_settings()
    if settings.fake_llm:
        return FakeLLMService()
    return GoogleLLMService()


@lru_cache(maxsize=1)
def get_query_rewriter_service():
    """
    Devuelve QueryRewriter si está habilitado (feature flag).
    """
    settings = get_settings()
    if not settings.enable_query_rewrite:
        return None
    return get_query_rewriter(get_llm_service(), enabled=settings.enable_query_rewrite)


@lru_cache(maxsize=1)
def get_chunk_reranker_service():
    """
    Devuelve ChunkReranker si está habilitado (feature flag).
    """
    settings = get_settings()
    if not settings.enable_rerank:
        return None
    return get_chunk_reranker(get_llm_service(), mode=RerankerMode.HEURISTIC)


@lru_cache(maxsize=1)
def get_rank_fusion_service() -> RankFusionService | None:
    """
    Devuelve RankFusionService si hybrid search está habilitado (feature flag).
    """
    settings = get_settings()
    if not settings.enable_hybrid_search:
        return None
    return RankFusionService(k=settings.rrf_k)


# =============================================================================
# Adapters de infraestructura (singletons)
# =============================================================================


@lru_cache(maxsize=1)
def get_text_chunker() -> TextChunkerService:
    """Chunker de texto configurado por Settings (tamaño y overlap)."""
    settings = get_settings()
    return SimpleTextChunker(
        chunk_size=settings.chunk_size,
        overlap=settings.chunk_overlap,
    )


@lru_cache(maxsize=1)
def get_file_storage() -> FileStoragePort | None:
    """
    Adapter de almacenamiento (S3/MinIO) si está configurado.

    Regla:
      - Si faltan parámetros requeridos, se deshabilita devolviendo None.
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


@lru_cache(maxsize=1)
def get_document_text_extractor() -> DocumentTextExtractor:
    """Extractor de texto (PDF/DOCX/TXT) por strategies internas."""
    return SimpleDocumentTextExtractor()


@lru_cache(maxsize=1)
def get_document_queue() -> DocumentProcessingQueue | None:
    """
    Cola para procesamiento en background (RQ/Redis) si está configurada.
    """
    settings = get_settings()
    if not settings.redis_url.strip():
        return None

    redis_conn = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=2,
        socket_timeout=5,
        health_check_interval=30,
    )

    config = RQQueueConfig(retry_max_attempts=settings.retry_max_attempts)
    return RQDocumentProcessingQueue(
        redis=redis_conn,
        config=config,
    )


# =============================================================================
# Casos de uso (factory por request)
# =============================================================================


def get_answer_query_use_case() -> AnswerQueryUseCase:
    """Caso de uso: responder pregunta con recuperación + generación."""
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
        enable_hybrid_search=settings.enable_hybrid_search,
        rank_fusion=get_rank_fusion_service(),
    )


def get_answer_query_with_history_use_case() -> AnswerQueryWithHistoryUseCase:
    """Caso de uso: chat con historial + rewriter opcional."""
    return AnswerQueryWithHistoryUseCase(
        conversation_repository=get_conversation_repository(),
        answer_query_use_case=get_answer_query_use_case(),
        query_rewriter=get_query_rewriter_service(),
    )


def get_ingest_document_use_case() -> IngestDocumentUseCase:
    """Caso de uso: ingesta directa de texto."""
    settings = get_settings()
    return IngestDocumentUseCase(
        repository=get_document_repository(),
        workspace_repository=get_workspace_repository(),
        embedding_service=get_embedding_service(),
        chunker=get_text_chunker(),
        enable_2tier_retrieval=settings.enable_2tier_retrieval,
        node_group_size=settings.node_group_size,
        node_text_max_chars=settings.node_text_max_chars,
    )


def get_search_chunks_use_case() -> SearchChunksUseCase:
    """Caso de uso: búsqueda de chunks (retrieval)."""
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
        enable_hybrid_search=settings.enable_hybrid_search,
        rank_fusion=get_rank_fusion_service(),
    )


def get_list_documents_use_case() -> ListDocumentsUseCase:
    """Caso de uso: listar documentos."""
    return ListDocumentsUseCase(
        document_repository=get_document_repository(),
        workspace_repository=get_workspace_repository(),
        acl_repository=get_workspace_acl_repository(),
    )


def get_list_workspaces_use_case() -> ListWorkspacesUseCase:
    """Caso de uso: listar workspaces."""
    return ListWorkspacesUseCase(
        workspace_repository=get_workspace_repository(),
        acl_repository=get_workspace_acl_repository(),
    )


def get_get_document_use_case() -> GetDocumentUseCase:
    """Caso de uso: obtener documento."""
    return GetDocumentUseCase(
        document_repository=get_document_repository(),
        workspace_repository=get_workspace_repository(),
        acl_repository=get_workspace_acl_repository(),
    )


def get_get_workspace_use_case() -> GetWorkspaceUseCase:
    """Caso de uso: obtener workspace."""
    return GetWorkspaceUseCase(
        workspace_repository=get_workspace_repository(),
        acl_repository=get_workspace_acl_repository(),
    )


def get_delete_document_use_case() -> DeleteDocumentUseCase:
    """Caso de uso: borrado lógico de documento."""
    return DeleteDocumentUseCase(
        document_repository=get_document_repository(),
        workspace_repository=get_workspace_repository(),
    )


def get_upload_document_use_case() -> UploadDocumentUseCase:
    """Caso de uso: subir documento (storage + enqueue opcional)."""
    return UploadDocumentUseCase(
        repository=get_document_repository(),
        workspace_repository=get_workspace_repository(),
        storage=get_file_storage(),
        queue=get_document_queue(),
    )


def get_reprocess_document_use_case() -> ReprocessDocumentUseCase:
    """Caso de uso: reprocesar documento (enqueue)."""
    return ReprocessDocumentUseCase(
        repository=get_document_repository(),
        workspace_repository=get_workspace_repository(),
        queue=get_document_queue(),
    )


def get_create_workspace_use_case() -> CreateWorkspaceUseCase:
    """Caso de uso: crear workspace."""
    return CreateWorkspaceUseCase(repository=get_workspace_repository())


def get_archive_workspace_use_case() -> ArchiveWorkspaceUseCase:
    """Caso de uso: archivar workspace (y sus documentos)."""
    return ArchiveWorkspaceUseCase(
        repository=get_workspace_repository(),
        document_repository=get_document_repository(),
    )


def get_update_workspace_use_case() -> UpdateWorkspaceUseCase:
    """Caso de uso: actualizar workspace."""
    return UpdateWorkspaceUseCase(repository=get_workspace_repository())


def get_publish_workspace_use_case() -> PublishWorkspaceUseCase:
    """Caso de uso: publicar workspace."""
    return PublishWorkspaceUseCase(repository=get_workspace_repository())


def get_share_workspace_use_case() -> ShareWorkspaceUseCase:
    """Caso de uso: compartir workspace (ACL)."""
    return ShareWorkspaceUseCase(
        repository=get_workspace_repository(),
        acl_repository=get_workspace_acl_repository(),
    )
