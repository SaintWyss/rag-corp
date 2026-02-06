"""
===============================================================================
USE CASE: Answer Query (Complete RAG Flow: Retrieval + Generation)
===============================================================================

Name:
    Answer Query Use Case

Business Goal:
    Responder una pregunta del usuario usando RAG:
      1) Embed del query
      2) Retrieval de chunks (similarity o MMR)
      3) Construcción de contexto con grounding (metadata)
      4) Generación con LLM basada únicamente en el contexto
      5) Observabilidad: timings + métricas + logs

Why (Context / Intención):
    - Este es el caso de uso “estrella” del sistema RAG.
    - Debe ser:
        * Independiente de infraestructura (PostgreSQL/Google/etc.) -> interfaces
        * Independiente de HTTP -> capa de presentación
        * Robusto (validaciones + manejo de fallas externas)
        * Observable (timings, conteo de fuentes, logs)
        * Seguro (filtro de prompt injection sobre chunks)

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    AnswerQueryUseCase

Responsibilities:
    - Validar input mínimo (workspace_id, query, top_k).
    - Enforce workspace read access (policy + ACL si corresponde).
    - Medir timings por etapa (embed/retrieve/llm).
    - Generar embedding del query (EmbeddingService).
    - Recuperar chunks (DocumentRepository) con similarity o MMR.
    - Aplicar filtro de inyección sobre chunks (apply_injection_filter).
    - Construir contexto (ContextBuilder) con metadata para grounding.
    - Generar respuesta con LLM (LLMService) usando contexto.
    - Reportar métricas (sources returned, stage metrics, refusals, etc.).
    - Devolver AnswerQueryResult con QueryResult estructurado o error tipado.

Collaborators:
    - DocumentRepository:
        find_similar_chunks(...)
        find_similar_chunks_mmr(...)
    - WorkspaceRepository, WorkspaceAclRepository:
        usados por resolve_workspace_for_read
    - EmbeddingService:
        embed_query(query) -> embedding vector
    - LLMService:
        generate_answer(query, context) -> str
    - ContextBuilder:
        build(chunks) -> (context: str, chunks_used: int)
    - StageTimings:
        measure(stage_name) context manager + to_dict()
    - Metrics/Logger:
        observe_sources_returned_count, record_answer_without_sources,
        record_policy_refusal, record_stage_metrics, logger

-------------------------------------------------------------------------------
INPUTS / OUTPUTS (Contrato del caso de uso)
-------------------------------------------------------------------------------
Inputs:
    AnswerQueryInput:
      - query: str
      - workspace_id: UUID
      - actor: WorkspaceActor | None
      - llm_query: Optional[str]
      - top_k: int (default 5)
      - use_mmr: bool

Outputs:
    AnswerQueryResult:
      - result: QueryResult | None
      - error: DocumentError | None

Error Mapping:
    - VALIDATION_ERROR:
        * workspace_id missing
        * query empty
        * top_k <= 0  (se responde con fallback “insufficient evidence” sin error)
    - FORBIDDEN / NOT_FOUND:
        * resueltos por resolve_workspace_for_read
    - SERVICE_UNAVAILABLE:
        * falla EmbeddingService / LLMService / repositorio (dependencias)
===============================================================================
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Final, Optional
from uuid import UUID

from ....crosscutting.logger import logger
from ....crosscutting.metrics import (
    observe_sources_returned_count,
    record_answer_without_sources,
    record_policy_refusal,
)
from ....crosscutting.timing import StageTimings
from ....domain.entities import QueryResult
from ....domain.repositories import (
    DocumentRepository,
    WorkspaceAclRepository,
    WorkspaceRepository,
)
from ....domain.services import EmbeddingService, LLMService
from ....domain.workspace_policy import WorkspaceActor
from ...context_builder import ContextBuilder, get_context_builder
from ...prompt_injection_detector import apply_injection_filter
from ...rank_fusion import RankFusionService
from ...reranker import ChunkReranker
from ..documents.document_results import (
    AnswerQueryResult,
    DocumentError,
    DocumentErrorCode,
)
from ..workspace.workspace_access import resolve_workspace_for_read

# -----------------------------------------------------------------------------
# Constantes: consistencia y evita strings mágicos.
# -----------------------------------------------------------------------------
_RESOURCE_WORKSPACE: Final[str] = "Workspace"
_RESOURCE_EMBEDDINGS: Final[str] = "EmbeddingService"
_RESOURCE_LLM: Final[str] = "LLMService"

_MSG_WORKSPACE_ID_REQUIRED: Final[str] = "workspace_id is required"
_MSG_QUERY_REQUIRED: Final[str] = "query is required"

# Mensaje de fallback (sin evidencia suficiente).
_MSG_INSUFFICIENT_EVIDENCE: Final[str] = (
    "No hay evidencia suficiente en las fuentes. ¿Podés precisar más (keywords/fecha/documento)?"
)

# Reglas defensivas de top_k (performance).
_DEFAULT_TOP_K: Final[int] = 5
_MAX_TOP_K: Final[int] = 50

# Reranking (defensivo y configurable).
_DEFAULT_RERANK_CANDIDATE_MULTIPLIER: Final[int] = 5
_DEFAULT_RERANK_MAX_CANDIDATES: Final[int] = 200

# Metadata keys (observabilidad consistente).
_META_RERANK_APPLIED: Final[str] = "rerank_applied"
_META_RERANK_CANDIDATES: Final[str] = "candidates_count"
_META_RERANK_RERANKED: Final[str] = "reranked_count"
_META_RERANK_SELECTED: Final[str] = "selected_top_k"
_META_HYBRID_USED: Final[str] = "hybrid_used"
_META_2TIER_USED: Final[str] = "2tier_used"

# Stage names para StageTimings (evita typos).
_STAGE_EMBED: Final[str] = "embed"
_STAGE_RETRIEVE: Final[str] = "retrieve"
_STAGE_LLM: Final[str] = "llm"


@dataclass(frozen=True)
class AnswerQueryInput:
    """
    DTO de entrada para AnswerQuery.

    Attributes:
        query: Pregunta del usuario (lenguaje natural)
        workspace_id: Scope del retrieval (aislamiento por workspace)
        actor: Contexto del actor (policy de acceso)
        llm_query: Override opcional del query para el prompt (si se quiere)
        top_k: Cantidad de chunks a recuperar (default: 5)
        use_mmr: True para retrieval diverso (MMR), False para similarity estándar
    """

    query: str
    workspace_id: UUID
    actor: WorkspaceActor | None
    llm_query: Optional[str] = None
    top_k: int = _DEFAULT_TOP_K
    use_mmr: bool = False


class AnswerQueryUseCase:
    """
    Use Case (Application Service / Orchestration):
        Orquesta el flujo completo de RAG: retrieval + generation.
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
        reranker: ChunkReranker | None = None,
        enable_rerank: bool = False,
        rerank_candidate_multiplier: int = _DEFAULT_RERANK_CANDIDATE_MULTIPLIER,
        rerank_max_candidates: int = _DEFAULT_RERANK_MAX_CANDIDATES,
        enable_hybrid_search: bool = False,
        rank_fusion: RankFusionService | None = None,
        enable_2tier_retrieval: bool = False,
        node_top_k: int = 10,
    ) -> None:
        self._documents = repository
        self._workspaces = workspace_repository
        self._acls = acl_repository
        self._embeddings = embedding_service
        self._llm = llm_service
        self._context_builder = context_builder or get_context_builder()

        # Config de seguridad (filtrado de prompt injection).
        self._injection_filter_mode = injection_filter_mode
        self._injection_risk_threshold = injection_risk_threshold

        # Config de reranking (feature flag + límites defensivos).
        self._reranker = reranker
        self._enable_rerank = enable_rerank
        self._rerank_candidate_multiplier = max(1, rerank_candidate_multiplier)
        self._rerank_max_candidates = max(_MAX_TOP_K, rerank_max_candidates)

        # Config de hybrid search (dense + sparse + RRF).
        self._enable_hybrid_search = enable_hybrid_search
        self._rank_fusion = rank_fusion

        # Config de 2-tier retrieval (nodes → chunks).
        self._enable_2tier_retrieval = enable_2tier_retrieval
        self._node_top_k = node_top_k

    def execute(self, input_data: AnswerQueryInput) -> AnswerQueryResult:
        """
        Ejecuta el flujo RAG:
          1) validar -> 2) policy -> 3) embed -> 4) retrieve -> 5) context -> 6) LLM

        Retorna:
          - AnswerQueryResult(result=QueryResult(...)) en éxito (incluso sin chunks)
          - AnswerQueryResult(error=DocumentError(...)) si falla por validación/policy/servicios
        """

        # ---------------------------------------------------------------------
        # 1) Validación mínima (barata).
        # ---------------------------------------------------------------------
        validation_error = self._validate_input(input_data)
        if validation_error is not None:
            return AnswerQueryResult(error=validation_error)

        # ---------------------------------------------------------------------
        # 2) Enforce acceso de lectura al workspace (policy centralizada).
        # ---------------------------------------------------------------------
        workspace, workspace_error = resolve_workspace_for_read(
            workspace_id=input_data.workspace_id,
            actor=input_data.actor,
            workspace_repository=self._workspaces,
            acl_repository=self._acls,
        )
        if workspace_error is not None:
            return AnswerQueryResult(error=workspace_error)

        # Extraer fts_language del workspace para hybrid search.
        from ....domain.entities import validate_fts_language

        fts_language = validate_fts_language(
            getattr(workspace, "fts_language", None)
        )

        # ---------------------------------------------------------------------
        # 3) Inicializar observabilidad.
        # ---------------------------------------------------------------------
        timings = StageTimings()
        prompt_version = getattr(self._llm, "prompt_version", "unknown")

        # ---------------------------------------------------------------------
        # 4) Sanitizar top_k (regla defensiva de performance).
        # ---------------------------------------------------------------------
        top_k = self._sanitize_top_k(input_data.top_k)
        candidate_top_k = self._compute_candidate_top_k(top_k)

        # Si top_k no permite retrieval, devolvemos fallback de forma explícita.
        # (No es un error de servicio/policy: es una configuración inválida.)
        if top_k <= 0:
            timing_data = timings.to_dict()
            return AnswerQueryResult(
                result=self._fallback_result(
                    input_data=input_data,
                    prompt_version=prompt_version,
                    timing_data=timing_data,
                    chunks_found=0,
                    chunks_used=0,
                    context_chars=0,
                    top_k=top_k,
                )
            )

        # ---------------------------------------------------------------------
        # 5) STEP: Embed query.
        # ---------------------------------------------------------------------
        try:
            with timings.measure(_STAGE_EMBED):
                query_embedding = self._embeddings.embed_query(input_data.query)
        except Exception:
            return AnswerQueryResult(
                error=self._service_unavailable(_RESOURCE_EMBEDDINGS)
            )

        # ---------------------------------------------------------------------
        # 6) STEP: Retrieve chunks.
        # ---------------------------------------------------------------------
        try:
            with timings.measure(_STAGE_RETRIEVE):
                chunks = self._retrieve_chunks(
                    query_text=input_data.query,
                    embedding=query_embedding,
                    workspace_id=input_data.workspace_id,
                    top_k=candidate_top_k,
                    use_mmr=input_data.use_mmr,
                    fts_language=fts_language,
                )
        except Exception:
            # Si el repositorio falla, es dependencia (DB/vector search).
            return AnswerQueryResult(
                error=self._service_unavailable("DocumentRepository")
            )

        # ---------------------------------------------------------------------
        # 7) Reranking (post-retrieval) antes de aplicar política de seguridad.
        # ---------------------------------------------------------------------
        # Motivo:
        #   - Queremos preservar el orden de relevancia del reranker.
        #   - Luego aplicamos la policy de inyección para mover/excluir riesgosos.
        rerank_result = self._maybe_rerank(
            query=input_data.query,
            chunks=chunks,
            top_k=top_k,
        )
        chunks = rerank_result["chunks"]

        # ---------------------------------------------------------------------
        # 8) Filtrado de seguridad (prompt injection) sobre chunks reordenados.
        # ---------------------------------------------------------------------
        filtered_chunks = apply_injection_filter(
            chunks,
            mode=self._injection_filter_mode,
            threshold=self._injection_risk_threshold,
        )
        chunks = filtered_chunks[:top_k]
        rerank_result["metadata"][_META_RERANK_SELECTED] = len(chunks)
        chunks_found = len(filtered_chunks)

        # ---------------------------------------------------------------------
        # 9) Si no hay chunks, devolvemos fallback (sin evidencia).
        # ---------------------------------------------------------------------
        if not chunks:
            timing_data = timings.to_dict()
            record_policy_refusal("insufficient_evidence")
            logger.info(
                "no chunks found for query",
                extra={
                    "context_chars": 0,
                    "prompt_version": prompt_version,
                    "chunks_found": chunks_found,
                    **timing_data,
                },
            )
            return AnswerQueryResult(
                result=self._fallback_result(
                    input_data=input_data,
                    prompt_version=prompt_version,
                    timing_data=timing_data,
                    chunks_found=chunks_found,
                    chunks_used=0,
                    context_chars=0,
                    top_k=top_k,
                    extra_metadata=rerank_result["metadata"],
                )
            )

        # ---------------------------------------------------------------------
        # 10) Construir contexto (grounding + metadata).
        # ---------------------------------------------------------------------
        context, chunks_used = self._context_builder.build(chunks)
        context_chars = len(context or "")

        # Defensa: si el builder decide usar 0, devolvemos fallback (sin evidencia).
        if chunks_used <= 0 or not context:
            timing_data = timings.to_dict()
            record_policy_refusal("insufficient_evidence")
            logger.info(
                "context builder produced empty context",
                extra={
                    "chunks_found": chunks_found,
                    "chunks_used": chunks_used,
                    "context_chars": context_chars,
                    "prompt_version": prompt_version,
                    **timing_data,
                },
            )
            return AnswerQueryResult(
                result=self._fallback_result(
                    input_data=input_data,
                    prompt_version=prompt_version,
                    timing_data=timing_data,
                    chunks_found=chunks_found,
                    chunks_used=0,
                    context_chars=context_chars,
                    top_k=top_k,
                    extra_metadata=rerank_result["metadata"],
                )
            )

        # ---------------------------------------------------------------------
        # 11) STEP: Generar respuesta con LLM.
        # ---------------------------------------------------------------------
        llm_query = input_data.llm_query or input_data.query
        try:
            with timings.measure(_STAGE_LLM):
                answer = self._llm.generate_answer(query=llm_query, context=context)
        except Exception:
            return AnswerQueryResult(error=self._service_unavailable(_RESOURCE_LLM))

        # ---------------------------------------------------------------------
        # 12) Observabilidad final (timings + log).
        # ---------------------------------------------------------------------
        timing_data = timings.to_dict()

        logger.info(
            "query answered",
            extra={
                "chunks_found": chunks_found,
                "chunks_used": chunks_used,
                "context_chars": context_chars,
                "prompt_version": prompt_version,
                **timing_data,
            },
        )

        # Métricas por etapas (si está disponible el helper).
        self._try_record_stage_metrics(timing_data)

        # Métricas sobre fuentes.
        observe_sources_returned_count(chunks_used)
        self._record_answer_source_hygiene(answer=answer, chunks_used=chunks_used)

        # ---------------------------------------------------------------------
        # 13) Retornar resultado estructurado.
        # ---------------------------------------------------------------------
        return AnswerQueryResult(
            result=QueryResult(
                answer=answer,
                # Solo incluir los chunks realmente usados en el contexto.
                chunks=chunks[:chunks_used],
                query=input_data.query,
                metadata={
                    "top_k": top_k,
                    "chunks_found": chunks_found,
                    "chunks_used": chunks_used,
                    "context_chars": context_chars,
                    "prompt_version": prompt_version,
                    "use_mmr": input_data.use_mmr,
                    **rerank_result["metadata"],
                    **timing_data,
                },
            )
        )

    # =========================================================================
    # Helpers privados: claridad, SRP y consistencia.
    # =========================================================================

    @staticmethod
    def _validate_input(input_data: AnswerQueryInput) -> DocumentError | None:
        """
        Valida input mínimo.

        Reglas:
          - workspace_id requerido
          - query requerido (no vacío tras strip)

        Nota:
          - top_k se sanitiza en _sanitize_top_k (no se considera fatal aquí).
        """
        if not input_data.workspace_id:
            return DocumentError(
                code=DocumentErrorCode.VALIDATION_ERROR,
                message=_MSG_WORKSPACE_ID_REQUIRED,
                resource=_RESOURCE_WORKSPACE,
            )

        if not (input_data.query or "").strip():
            return DocumentError(
                code=DocumentErrorCode.VALIDATION_ERROR,
                message=_MSG_QUERY_REQUIRED,
                resource="Query",
            )

        return None

    @staticmethod
    def _sanitize_top_k(top_k: int) -> int:
        """
        Aplica reglas defensivas a top_k para proteger performance.

        Reglas:
          - top_k <= 0 => se respeta (devolverá fallback)
          - top_k > MAX => clamp a MAX
        """
        if top_k <= 0:
            return top_k
        return min(top_k, _MAX_TOP_K)

    def _retrieve_chunks(
        self,
        *,
        query_text: str,
        embedding: list[float],
        workspace_id: UUID,
        top_k: int,
        use_mmr: bool,
        fts_language: str = "spanish",
    ):
        """
        Recupera chunks usando dense retrieval (similarity/MMR).

        Si 2-tier retrieval está habilitado, delega a _retrieve_chunks_2tier.
        Si hybrid search está habilitado, también ejecuta sparse retrieval
        (full-text search) y fusiona ambos rankings con RRF.
        """
        if self._2tier_enabled():
            return self._retrieve_chunks_2tier(
                embedding=embedding,
                workspace_id=workspace_id,
                top_k=top_k,
            )

        from ....crosscutting.metrics import (
            observe_dense_latency,
            observe_fusion_latency,
            observe_sparse_latency,
            record_retrieval_fallback,
        )

        # Dense retrieval (siempre se ejecuta)
        t0 = time.perf_counter()
        if use_mmr:
            fetch_k = self._compute_mmr_fetch_k(top_k)
            dense_results = self._documents.find_similar_chunks_mmr(
                embedding=embedding,
                top_k=top_k,
                fetch_k=fetch_k,
                lambda_mult=0.5,
                workspace_id=workspace_id,
            )
        else:
            dense_results = self._documents.find_similar_chunks(
                embedding=embedding,
                top_k=top_k,
                workspace_id=workspace_id,
            )
        observe_dense_latency(time.perf_counter() - t0)

        # Si hybrid no está habilitado, retornar solo dense
        if not self._hybrid_enabled():
            return dense_results

        # Sparse retrieval (full-text search)
        try:
            t0 = time.perf_counter()
            sparse_results = self._documents.find_chunks_full_text(
                query_text=query_text,
                top_k=top_k,
                workspace_id=workspace_id,
                fts_language=fts_language,
            )
            observe_sparse_latency(time.perf_counter() - t0)
        except Exception as exc:
            record_retrieval_fallback("sparse")
            logger.warning(
                "Sparse retrieval failed, using dense-only",
                extra={"error": str(exc)},
            )
            return dense_results

        # Fusionar con RRF
        assert self._rank_fusion is not None
        t0 = time.perf_counter()
        fused = self._rank_fusion.fuse(dense_results, sparse_results)
        observe_fusion_latency(time.perf_counter() - t0)
        return fused

    def _compute_candidate_top_k(self, top_k: int) -> int:
        """
        Calcula cuántos candidatos pedir al repositorio.

        Regla:
          - Si rerank está habilitado, pedir más candidatos para reordenar.
          - Mantener límites defensivos para evitar costos explosivos.
        """
        if top_k <= 0:
            return top_k

        if not self._rerank_enabled():
            return top_k

        expanded = top_k * self._rerank_candidate_multiplier
        return min(max(top_k, expanded), self._rerank_max_candidates)

    def _compute_mmr_fetch_k(self, top_k: int) -> int:
        """
        Define fetch_k para MMR con límite defensivo.

        Razón:
          - MMR necesita más candidatos para diversidad.
          - No debe superar el máximo configurado.
        """
        if top_k <= 0:
            return top_k

        fetch_k = top_k * 4
        if not self._rerank_enabled():
            return max(top_k, fetch_k)
        return min(max(top_k, fetch_k), self._rerank_max_candidates)

    def _rerank_enabled(self) -> bool:
        """
        Feature flag efectiva de reranking.

        Nota:
          - Se requiere flag habilitado y reranker inyectado.
        """
        return bool(self._enable_rerank and self._reranker is not None)

    def _hybrid_enabled(self) -> bool:
        """
        Feature flag efectiva de hybrid search.

        Requiere flag habilitado y RankFusionService inyectado.
        """
        return bool(self._enable_hybrid_search and self._rank_fusion is not None)

    def _2tier_enabled(self) -> bool:
        """Feature flag efectiva de 2-tier retrieval."""
        return bool(self._enable_2tier_retrieval)

    def _retrieve_chunks_2tier(
        self,
        *,
        embedding: list[float],
        workspace_id: UUID,
        top_k: int,
    ):
        """
        Retrieval jerárquico 2-tier: nodos → chunks.

        Flujo:
          1) Buscar nodos similares al query (coarse).
          2) Si no hay nodos → fallback a dense retrieval estándar.
          3) Obtener chunks dentro de los spans de los nodos.
          4) Rankear chunks por cosine similarity al query embedding.
          5) Retornar top_k chunks.
        """
        from ....crosscutting.metrics import record_retrieval_fallback

        # 1) Coarse: buscar nodos
        nodes = self._documents.find_similar_nodes(
            embedding=embedding,
            top_k=self._node_top_k,
            workspace_id=workspace_id,
        )

        # 2) Fallback si no hay nodos
        if not nodes:
            record_retrieval_fallback("2tier_no_nodes")
            return self._documents.find_similar_chunks(
                embedding=embedding,
                top_k=top_k,
                workspace_id=workspace_id,
            )

        # 3) Fine: obtener chunks dentro de los spans
        node_spans = [
            (n.document_id, n.span_start, n.span_end)
            for n in nodes
            if n.document_id and n.span_start is not None and n.span_end is not None
        ]

        if not node_spans:
            record_retrieval_fallback("2tier_no_spans")
            return self._documents.find_similar_chunks(
                embedding=embedding,
                top_k=top_k,
                workspace_id=workspace_id,
            )

        chunks = self._documents.find_chunks_by_node_spans(
            node_spans=node_spans,
            workspace_id=workspace_id,
        )

        if not chunks:
            return []

        # 4) Rankear chunks por cosine similarity (pure Python, no numpy)
        def _cosine_sim(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return dot / (norm_a * norm_b)

        scored = [
            (chunk, _cosine_sim(embedding, chunk.embedding))
            for chunk in chunks
            if chunk.embedding
        ]
        scored.sort(key=lambda x: x[1], reverse=True)

        # 5) Top-k con similarity asignada
        result = []
        for chunk, sim in scored[:top_k]:
            chunk.similarity = sim
            result.append(chunk)

        return result

    def _maybe_rerank(
        self,
        *,
        query: str,
        chunks: list,
        top_k: int,
    ) -> dict:
        """
        Aplica reranking si está habilitado y retorna metadata consistente.

        Contrato:
          - Si falla el reranker, retorna el orden original (fallback seguro).
          - Siempre devuelve metadata útil para observabilidad.
        """
        from ....crosscutting.metrics import (
            observe_rerank_latency,
            record_retrieval_fallback,
        )

        candidates_count = len(chunks)
        default_metadata = {
            _META_RERANK_APPLIED: False,
            _META_RERANK_CANDIDATES: candidates_count,
            _META_RERANK_RERANKED: 0,
            _META_RERANK_SELECTED: min(top_k, candidates_count),
            _META_HYBRID_USED: self._hybrid_enabled(),
        }

        if not self._rerank_enabled() or candidates_count <= 0:
            return {
                "chunks": chunks,
                "metadata": default_metadata,
            }

        try:
            # R: Pedimos rerank sobre todos los candidatos para luego recortar.
            t0 = time.perf_counter()
            result = self._reranker.rerank(
                query=query,
                chunks=chunks,
                top_k=min(candidates_count, self._rerank_max_candidates),
            )
            observe_rerank_latency(time.perf_counter() - t0)
            reranked_chunks = result.chunks
            return {
                "chunks": reranked_chunks,
                "metadata": {
                    _META_RERANK_APPLIED: True,
                    _META_RERANK_CANDIDATES: candidates_count,
                    _META_RERANK_RERANKED: result.original_count,
                    _META_RERANK_SELECTED: len(reranked_chunks[:top_k]),
                    _META_HYBRID_USED: self._hybrid_enabled(),
                },
            }
        except Exception as exc:
            record_retrieval_fallback("rerank")
            logger.warning(
                "Reranking failed, using original order",
                extra={
                    "error": str(exc),
                    "candidates_count": candidates_count,
                },
            )
            return {
                "chunks": chunks,
                "metadata": default_metadata,
            }

    @staticmethod
    def _fallback_result(
        *,
        input_data: AnswerQueryInput,
        prompt_version: str,
        timing_data: dict,
        chunks_found: int,
        chunks_used: int,
        context_chars: int,
        top_k: int,
        extra_metadata: dict | None = None,
    ) -> QueryResult:
        """
        Construye un QueryResult de fallback consistente (sin evidencia suficiente).
        """
        metadata = {
            "top_k": top_k,
            "chunks_found": chunks_found,
            "chunks_used": chunks_used,
            "context_chars": context_chars,
            "prompt_version": prompt_version,
            **timing_data,
        }
        if extra_metadata:
            metadata.update(extra_metadata)
        return QueryResult(
            answer=_MSG_INSUFFICIENT_EVIDENCE,
            chunks=[],
            query=input_data.query,
            metadata=metadata,
        )

    @staticmethod
    def _service_unavailable(resource: str) -> DocumentError:
        """
        Error consistente para fallas de dependencias externas (embeddings, LLM, repo).
        """
        return DocumentError(
            code=DocumentErrorCode.SERVICE_UNAVAILABLE,
            message=f"{resource} is unavailable.",
            resource=resource,
        )

    @staticmethod
    def _try_record_stage_metrics(timing_data: dict) -> None:
        """
        Registra métricas por etapa si el helper está disponible.

        Nota:
          - Se mantiene desacoplado con import lazy para no crear dependencias fuertes.
        """
        try:
            from ....crosscutting.metrics import record_stage_metrics

            record_stage_metrics(
                embed_seconds=timing_data.get("embed_ms", 0) / 1000,
                retrieve_seconds=timing_data.get("retrieve_ms", 0) / 1000,
                llm_seconds=timing_data.get("llm_ms", 0) / 1000,
            )
        except Exception:
            # Silencioso: métricas no deben romper el caso de uso.
            return

    @staticmethod
    def _record_answer_source_hygiene(*, answer: str | None, chunks_used: int) -> None:
        """
        Métrica de “higiene” de fuentes:
          - Si hubo fuentes usadas, pero el texto no menciona fuentes,
            registramos el evento (observabilidad).
        """
        if chunks_used <= 0:
            return

        answer_lower = (answer or "").lower()
        if "fuentes" not in answer_lower and "[s" not in answer_lower:
            record_answer_without_sources()
