"""
Name: Answer Query Use Case

Responsibilities:
  - Orchestrate complete RAG flow (retrieval + generation)
  - Coordinate repository, embedding service, and LLM service
  - Build context with metadata using ContextBuilder
  - Apply business logic (top_k, context limits, error handling)
  - Return QueryResult with answer and sources
  - Measure and report stage timings

Collaborators:
  - domain.repositories.DocumentRepository: Chunk retrieval
  - domain.services.EmbeddingService: Query embedding generation
  - domain.services.LLMService: Answer generation
  - domain.entities.QueryResult: Response encapsulation
  - application.context_builder: Context assembly with metadata
  - timing.StageTimings: Performance measurement

Constraints:
  - No HTTP concerns (that's the presentation layer's job)
  - No knowledge of PostgreSQL, Google API, etc. (abstracted by interfaces)
  - Business logic only (orchestration + rules)

Notes:
  - This is the "star" use case of the RAG system
  - Context includes grounding metadata (doc ID, chunk index)
  - Logs context_chars, prompt_version for observability
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from ...domain.entities import QueryResult
from .document_results import DocumentError, DocumentErrorCode
from ...domain.repositories import (
    DocumentRepository,
    WorkspaceRepository,
    WorkspaceAclRepository,
)
from ...domain.services import EmbeddingService, LLMService
from ...domain.workspace_policy import WorkspaceActor
from ...crosscutting.timing import StageTimings
from ...crosscutting.metrics import (
    observe_sources_returned_count,
    record_answer_without_sources,
    record_policy_refusal,
)
from ...crosscutting.logger import logger
from ..context_builder import ContextBuilder, get_context_builder
from ..prompt_injection_detector import apply_injection_filter
from .document_results import AnswerQueryResult
from .workspace_access import resolve_workspace_for_read


@dataclass
class AnswerQueryInput:
    """
    R: Input data for AnswerQuery use case.

    Attributes:
        query: User's natural language question
        workspace_id: Workspace UUID for scoping retrieval
        actor: Actor context for workspace access
        llm_query: Optional query override passed to the LLM prompt
        top_k: Number of similar chunks to retrieve (default: 5)
        use_mmr: Use Maximal Marginal Relevance for diverse results
    """

    query: str
    workspace_id: UUID
    actor: WorkspaceActor | None
    llm_query: Optional[str] = None
    top_k: int = 5
    use_mmr: bool = False


class AnswerQueryUseCase:
    """
    R: Use case for complete RAG flow (retrieval + generation).

    This is the main business logic for answering user questions
    using retrieved context from the document repository.
    """

    def __init__(
        self,
        repository: DocumentRepository,
        workspace_repository: WorkspaceRepository,
        acl_repository: WorkspaceAclRepository,
        embedding_service: EmbeddingService,
        llm_service: LLMService,
        context_builder: Optional[ContextBuilder] = None,
        injection_filter_mode: str = "off",
        injection_risk_threshold: float = 0.6,
    ):
        """
        R: Initialize use case with injected dependencies.

        Args:
            repository: Document repository for chunk retrieval
            embedding_service: Service for generating embeddings
            llm_service: Service for generating answers
            context_builder: Optional context builder (defaults to singleton)
        """
        self.repository = repository
        self.workspace_repository = workspace_repository
        self.acl_repository = acl_repository
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        self.context_builder = context_builder or get_context_builder()
        self.injection_filter_mode = injection_filter_mode
        self.injection_risk_threshold = injection_risk_threshold

    def execute(self, input_data: AnswerQueryInput) -> AnswerQueryResult:
        """
        R: Execute RAG flow: embed query → retrieve chunks → generate answer.

        Args:
            input_data: Query and configuration (top_k)

        Returns:
            QueryResult with generated answer and source chunks

        Business Rules:
            1. If no chunks found, return "not found" message
            2. Context is assembled with metadata for grounding
            3. LLM must answer based only on provided context
        """
        if not input_data.workspace_id:
            return AnswerQueryResult(
                error=DocumentError(
                    code=DocumentErrorCode.VALIDATION_ERROR,
                    message="workspace_id is required",
                    resource="Workspace",
                )
            )
        _, error = resolve_workspace_for_read(
            workspace_id=input_data.workspace_id,
            actor=input_data.actor,
            workspace_repository=self.workspace_repository,
            acl_repository=self.acl_repository,
        )
        if error:
            return AnswerQueryResult(error=error)

        # R: Initialize timing measurement
        timings = StageTimings()

        # R: Get prompt version for logging
        prompt_version = getattr(self.llm_service, "prompt_version", "unknown")

        if input_data.top_k <= 0:
            timing_data = timings.to_dict()
            return AnswerQueryResult(
                result=QueryResult(
                    answer="No hay evidencia suficiente en las fuentes. ¿Podés precisar más (keywords/fecha/documento)?",
                    chunks=[],
                    query=input_data.query,
                    metadata={
                        "top_k": input_data.top_k,
                        "chunks_found": 0,
                        "context_chars": 0,
                        "prompt_version": prompt_version,
                        **timing_data,
                    },
                )
            )

        # R: STEP 1 - Generate query embedding
        with timings.measure("embed"):
            query_embedding = self.embedding_service.embed_query(input_data.query)

        # R: STEP 2 - Retrieve similar chunks from repository
        with timings.measure("retrieve"):
            if input_data.use_mmr:
                # R: MMR for diverse retrieval (avoids redundant chunks)
                chunks = self.repository.find_similar_chunks_mmr(
                    embedding=query_embedding,
                    top_k=input_data.top_k,
                    fetch_k=input_data.top_k * 4,  # Fetch 4x for better diversity
                    lambda_mult=0.5,
                    workspace_id=input_data.workspace_id,
                )
            else:
                # R: Standard similarity search (faster)
                chunks = self.repository.find_similar_chunks(
                    embedding=query_embedding,
                    top_k=input_data.top_k,
                    workspace_id=input_data.workspace_id,
                )

        chunks = apply_injection_filter(
            chunks,
            mode=self.injection_filter_mode,
            threshold=self.injection_risk_threshold,
        )

        # R: STEP 3 - Assemble context from retrieved chunks
        if not chunks:
            # R: Business rule: If no relevant chunks, return fallback message
            timing_data = timings.to_dict()
            record_policy_refusal("insufficient_evidence")
            logger.info(
                "no chunks found for query",
                extra={
                    "context_chars": 0,
                    "prompt_version": prompt_version,
                    **timing_data,
                },
            )
            return AnswerQueryResult(
                result=QueryResult(
                    answer="No hay evidencia suficiente en las fuentes. ¿Podés precisar más (keywords/fecha/documento)?",
                    chunks=[],
                    query=input_data.query,
                    metadata={
                        "top_k": input_data.top_k,
                        "chunks_found": 0,
                        "context_chars": 0,
                        "prompt_version": prompt_version,
                        **timing_data,
                    },
                )
            )

        # R: Build context with metadata using ContextBuilder
        context, chunks_used = self.context_builder.build(chunks)
        context_chars = len(context)

        # R: STEP 4 - Generate answer using LLM
        llm_query = input_data.llm_query or input_data.query

        with timings.measure("llm"):
            answer = self.llm_service.generate_answer(query=llm_query, context=context)

        # R: Get final timing data
        timing_data = timings.to_dict()

        # R: Log successful query with extended fields
        logger.info(
            "query answered",
            extra={
                "chunks_found": len(chunks),
                "chunks_used": chunks_used,
                "context_chars": context_chars,
                "prompt_version": prompt_version,
                **timing_data,
            },
        )

        # R: Record metrics (optional, lazy import)
        try:
            from ...crosscutting.metrics import record_stage_metrics

            record_stage_metrics(
                embed_seconds=timing_data.get("embed_ms", 0) / 1000,
                retrieve_seconds=timing_data.get("retrieve_ms", 0) / 1000,
                llm_seconds=timing_data.get("llm_ms", 0) / 1000,
            )
        except ImportError:
            pass

        # R: Return structured result with answer and sources
        observe_sources_returned_count(chunks_used)
        if chunks_used > 0:
            answer_lower = (answer or "").lower()
            if "fuentes" not in answer_lower and "[s" not in answer_lower:
                record_answer_without_sources()
        return AnswerQueryResult(
            result=QueryResult(
                answer=answer,
                chunks=chunks[:chunks_used],  # Only include chunks actually used
                query=input_data.query,
                metadata={
                    "top_k": input_data.top_k,
                    "chunks_found": len(chunks),
                    "chunks_used": chunks_used,
                    "context_chars": context_chars,
                    "prompt_version": prompt_version,
                    "use_mmr": input_data.use_mmr,
                    **timing_data,
                },
            )
        )
