"""
===============================================================================
ARCHIVO: crosscutting/metrics.py
===============================================================================

CRC CARD (Módulo)
-------------------------------------------------------------------------------
Nombre:
    Métricas (Prometheus) — Observabilidad de bajo acoplamiento

Responsabilidades:
    - Definir métricas Prometheus (si la dependencia existe) sin romper el runtime.
    - Proveer funciones pequeñas y estables para registrar eventos/duraciones.
    - Cuidar cardinalidad (NO user_id, NO SQL completo, NO IDs dinámicos).
    - Exponer helpers para generar la respuesta /metrics.

Colaboradores:
    - crosscutting.middleware: registra latencia y conteo HTTP.
    - application/usecases: registra timings de etapas RAG.
    - infrastructure/db/instrumentation: observa duración de queries.
    - worker/jobs: registra métricas de procesamiento asíncrono.

Decisiones de diseño (Senior):
    - "Dependencia opcional": si `prometheus_client` no está instalado,
      TODO funciona igual (no-op). Esto mantiene el backend portable.
    - Registro único global: Prometheus requiere singletons.
    - Normalización de paths: evita explosión de cardinalidad.
===============================================================================
"""

from __future__ import annotations

import re
from typing import Optional

# -----------------------------------------------------------------------------
# Dependencia opcional (prometheus_client)
# -----------------------------------------------------------------------------

_prometheus_available = False
_registry = None

try:
    from prometheus_client import (  # type: ignore
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        Counter,
        Histogram,
        generate_latest,
    )

    _prometheus_available = True
    _registry = CollectorRegistry()
except ImportError:
    # Si no está instalado, el módulo queda en modo no-op.
    pass


# -----------------------------------------------------------------------------
# Métricas (variables globales)
# -----------------------------------------------------------------------------

_requests_total: Optional["Counter"] = None
_request_latency: Optional["Histogram"] = None

_embed_latency: Optional["Histogram"] = None
_retrieve_latency: Optional["Histogram"] = None
_llm_latency: Optional["Histogram"] = None

_embedding_cache_hits: Optional["Counter"] = None
_embedding_cache_misses: Optional["Counter"] = None

_worker_processed_total: Optional["Counter"] = None
_worker_failed_total: Optional["Counter"] = None
_worker_duration: Optional["Histogram"] = None

_policy_refusal_total: Optional["Counter"] = None
_prompt_injection_detected_total: Optional["Counter"] = None
_cross_scope_block_total: Optional["Counter"] = None
_answer_without_sources_total: Optional["Counter"] = None

_sources_returned_count: Optional["Histogram"] = None

# Dedup
_dedup_hit_total: Optional["Counter"] = None

# Hybrid retrieval
_hybrid_retrieval_total: Optional["Counter"] = None

# Pipeline stages (sub-stage detail)
_dense_latency: Optional["Histogram"] = None
_sparse_latency: Optional["Histogram"] = None
_fusion_latency: Optional["Histogram"] = None
_rerank_latency: Optional["Histogram"] = None
_retrieval_fallback_total: Optional["Counter"] = None

# DB (baja cardinalidad)
_db_query_duration: Optional["Histogram"] = None

# Connector sync
_connector_files_created_total: Optional["Counter"] = None
_connector_files_updated_total: Optional["Counter"] = None
_connector_files_skipped_unchanged_total: Optional["Counter"] = None


def _init_metrics() -> None:
    """Inicializa métricas (una sola vez)."""
    global _requests_total, _request_latency
    global _embed_latency, _retrieve_latency, _llm_latency
    global _embedding_cache_hits, _embedding_cache_misses
    global _worker_processed_total, _worker_failed_total, _worker_duration
    global _policy_refusal_total, _prompt_injection_detected_total
    global _cross_scope_block_total, _answer_without_sources_total
    global _sources_returned_count, _dedup_hit_total, _hybrid_retrieval_total
    global _db_query_duration
    global _dense_latency, _sparse_latency, _fusion_latency
    global _rerank_latency, _retrieval_fallback_total
    global _connector_files_created_total, _connector_files_updated_total
    global _connector_files_skipped_unchanged_total

    if not _prometheus_available or _requests_total is not None:
        return

    # ------------------------
    # HTTP
    # ------------------------
    _requests_total = Counter(
        "rag_requests_total",
        "Total de requests HTTP",
        ["endpoint", "method", "status"],
        registry=_registry,
    )

    _request_latency = Histogram(
        "rag_request_latency_seconds",
        "Latencia de requests HTTP (segundos)",
        ["endpoint", "method"],
        buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        registry=_registry,
    )

    # ------------------------
    # Etapas RAG
    # ------------------------
    _embed_latency = Histogram(
        "rag_embed_latency_seconds",
        "Latencia de generación de embeddings (segundos)",
        buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
        registry=_registry,
    )

    _retrieve_latency = Histogram(
        "rag_retrieve_latency_seconds",
        "Latencia de retrieval de chunks (segundos)",
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
        registry=_registry,
    )

    _llm_latency = Histogram(
        "rag_llm_latency_seconds",
        "Latencia de generación del LLM (segundos)",
        buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
        registry=_registry,
    )

    # ------------------------
    # Cache embeddings
    # ------------------------
    _embedding_cache_hits = Counter(
        "rag_embedding_cache_hit_total",
        "Hits del cache de embeddings",
        ["kind"],
        registry=_registry,
    )

    _embedding_cache_misses = Counter(
        "rag_embedding_cache_miss_total",
        "Misses del cache de embeddings",
        ["kind"],
        registry=_registry,
    )

    # ------------------------
    # Worker
    # ------------------------
    _worker_processed_total = Counter(
        "rag_worker_processed_total",
        "Total de documentos procesados por el worker",
        ["status"],
        registry=_registry,
    )

    _worker_failed_total = Counter(
        "rag_worker_failed_total",
        "Total de fallos del worker",
        registry=_registry,
    )

    _worker_duration = Histogram(
        "rag_worker_duration_seconds",
        "Duración del procesamiento del worker (segundos)",
        buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
        registry=_registry,
    )

    # ------------------------
    # Seguridad / calidad
    # ------------------------
    _policy_refusal_total = Counter(
        "rag_policy_refusal_total",
        "Total de rechazos por política",
        ["reason"],
        registry=_registry,
    )

    _prompt_injection_detected_total = Counter(
        "rag_prompt_injection_detected_total",
        "Detecciones de prompt injection por patrón",
        ["pattern"],
        registry=_registry,
    )

    _cross_scope_block_total = Counter(
        "rag_cross_scope_block_total",
        "Bloqueos por cross-scope o scope faltante",
        registry=_registry,
    )

    _answer_without_sources_total = Counter(
        "rag_answer_without_sources_total",
        "Respuestas devueltas sin sección de fuentes",
        registry=_registry,
    )

    _sources_returned_count = Histogram(
        "rag_sources_returned_count",
        "Cantidad de fuentes devueltas",
        buckets=(0, 1, 2, 3, 5, 8, 13, 21),
        registry=_registry,
    )

    # ------------------------
    # Dedup
    # ------------------------
    _dedup_hit_total = Counter(
        "rag_dedup_hit_total",
        "Documentos rechazados por deduplicación de contenido",
        registry=_registry,
    )

    # ------------------------
    # Hybrid retrieval
    # ------------------------
    _hybrid_retrieval_total = Counter(
        "rag_hybrid_retrieval_total",
        "Requests que usaron hybrid retrieval (dense+sparse+RRF)",
        ["endpoint"],
        registry=_registry,
    )

    # Pipeline stages (sub-stage)
    # ------------------------
    _dense_latency = Histogram(
        "rag_dense_latency_seconds",
        "Latencia de dense retrieval — similarity/MMR (segundos)",
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
        registry=_registry,
    )

    _sparse_latency = Histogram(
        "rag_sparse_latency_seconds",
        "Latencia de sparse retrieval — full-text search (segundos)",
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
        registry=_registry,
    )

    _fusion_latency = Histogram(
        "rag_fusion_latency_seconds",
        "Latencia de RRF fusion (segundos)",
        buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05),
        registry=_registry,
    )

    _rerank_latency = Histogram(
        "rag_rerank_latency_seconds",
        "Latencia de reranking (segundos)",
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
        registry=_registry,
    )

    _retrieval_fallback_total = Counter(
        "rag_retrieval_fallback_total",
        "Fallbacks por falla en una etapa de retrieval",
        ["stage"],
        registry=_registry,
    )

    # ------------------------
    # DB
    # ------------------------
    _db_query_duration = Histogram(
        "rag_db_query_duration_seconds",
        "Duración de queries DB (segundos)",
        ["kind"],
        buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
        registry=_registry,
    )

    # ------------------------
    # Connector sync
    # ------------------------
    _connector_files_created_total = Counter(
        "rag_connector_files_created_total",
        "Archivos creados (nuevos) por sync de conectores",
        registry=_registry,
    )

    _connector_files_updated_total = Counter(
        "rag_connector_files_updated_total",
        "Archivos actualizados (re-ingestados) por sync de conectores",
        registry=_registry,
    )

    _connector_files_skipped_unchanged_total = Counter(
        "rag_connector_files_skipped_unchanged_total",
        "Archivos omitidos (sin cambios) por sync de conectores",
        registry=_registry,
    )


# Inicialización al importar el módulo
_init_metrics()


# -----------------------------------------------------------------------------
# API pública (helpers de registro)
# -----------------------------------------------------------------------------


def record_request_metrics(
    endpoint: str,
    method: str,
    status_code: int,
    latency_seconds: float,
) -> None:
    """Registra métricas HTTP.

    - endpoint se normaliza para no explotar cardinalidad.
    - status se agrupa por 2xx/4xx/5xx.
    """
    if not _prometheus_available:
        return

    normalized = _normalize_endpoint(endpoint)
    status_bucket = _status_bucket(status_code)

    if _requests_total:
        _requests_total.labels(
            endpoint=normalized,
            method=method,
            status=status_bucket,
        ).inc()

    if _request_latency:
        _request_latency.labels(endpoint=normalized, method=method).observe(
            latency_seconds
        )


def record_stage_metrics(
    embed_seconds: Optional[float] = None,
    retrieve_seconds: Optional[float] = None,
    llm_seconds: Optional[float] = None,
) -> None:
    """Registra timings del pipeline RAG."""
    if not _prometheus_available:
        return

    if embed_seconds is not None and _embed_latency:
        _embed_latency.observe(embed_seconds)

    if retrieve_seconds is not None and _retrieve_latency:
        _retrieve_latency.observe(retrieve_seconds)

    if llm_seconds is not None and _llm_latency:
        _llm_latency.observe(llm_seconds)


def record_embedding_cache_hit(count: int = 1, kind: str = "query") -> None:
    """Incrementa hits del cache de embeddings."""
    if not _prometheus_available:
        return
    if _embedding_cache_hits:
        _embedding_cache_hits.labels(kind=kind).inc(count)


def record_embedding_cache_miss(count: int = 1, kind: str = "query") -> None:
    """Incrementa misses del cache de embeddings."""
    if not _prometheus_available:
        return
    if _embedding_cache_misses:
        _embedding_cache_misses.labels(kind=kind).inc(count)


def observe_db_query_duration(kind: str, seconds: float) -> None:
    """Observa duración de una query DB.

    Reglas:
      - `kind` debe ser baja cardinalidad (SELECT/INSERT/UPDATE/...).
      - NO incluir SQL completo.
    """
    if not _prometheus_available:
        return
    if _db_query_duration:
        _db_query_duration.labels(kind=(kind or "UNKNOWN").upper()).observe(seconds)


def record_worker_processed(status: str) -> None:
    """Cuenta documentos procesados por status."""
    if not _prometheus_available:
        return
    if _worker_processed_total:
        _worker_processed_total.labels(status=status).inc()


def record_worker_failed(count: int = 1) -> None:
    """Cuenta fallos del worker."""
    if not _prometheus_available:
        return
    if _worker_failed_total:
        _worker_failed_total.inc(count)


def observe_worker_duration(duration_seconds: float) -> None:
    """Observa duración del worker."""
    if not _prometheus_available:
        return
    if _worker_duration:
        _worker_duration.observe(duration_seconds)


def record_policy_refusal(reason: str) -> None:
    """Cuenta rechazos por política."""
    if not _prometheus_available:
        return
    if _policy_refusal_total:
        _policy_refusal_total.labels(reason=reason).inc()


def record_prompt_injection_detected(pattern: str) -> None:
    """Cuenta detecciones de prompt injection por patrón."""
    if not _prometheus_available:
        return
    if _prompt_injection_detected_total:
        _prompt_injection_detected_total.labels(pattern=pattern).inc()


def record_cross_scope_block(count: int = 1) -> None:
    """Cuenta bloqueos por scope."""
    if not _prometheus_available:
        return
    if _cross_scope_block_total:
        _cross_scope_block_total.inc(count)


def record_answer_without_sources(count: int = 1) -> None:
    """Cuenta respuestas sin fuentes."""
    if not _prometheus_available:
        return
    if _answer_without_sources_total:
        _answer_without_sources_total.inc(count)


def observe_sources_returned_count(count: int) -> None:
    """Observa cuántas fuentes se devolvieron."""
    if not _prometheus_available:
        return
    if _sources_returned_count:
        _sources_returned_count.observe(count)


def record_dedup_hit(count: int = 1) -> None:
    """Cuenta documentos rechazados por deduplicación de contenido."""
    if not _prometheus_available:
        return
    if _dedup_hit_total:
        _dedup_hit_total.inc(count)


def record_hybrid_retrieval(endpoint: str) -> None:
    """Cuenta requests que usaron hybrid retrieval (dense+sparse+RRF).

    Args:
        endpoint: identificador del endpoint (baja cardinalidad: "ask" | "ask_stream").
    """
    if not _prometheus_available:
        return
    if _hybrid_retrieval_total:
        _hybrid_retrieval_total.labels(endpoint=endpoint).inc()


def observe_dense_latency(seconds: float) -> None:
    """Observa latencia de dense retrieval (similarity/MMR)."""
    if not _prometheus_available:
        return
    if _dense_latency:
        _dense_latency.observe(seconds)


def observe_sparse_latency(seconds: float) -> None:
    """Observa latencia de sparse retrieval (full-text search)."""
    if not _prometheus_available:
        return
    if _sparse_latency:
        _sparse_latency.observe(seconds)


def observe_fusion_latency(seconds: float) -> None:
    """Observa latencia de RRF fusion."""
    if not _prometheus_available:
        return
    if _fusion_latency:
        _fusion_latency.observe(seconds)


def observe_rerank_latency(seconds: float) -> None:
    """Observa latencia de reranking."""
    if not _prometheus_available:
        return
    if _rerank_latency:
        _rerank_latency.observe(seconds)


def record_retrieval_fallback(stage: str) -> None:
    """Cuenta fallbacks por falla en una etapa de retrieval.

    Args:
        stage: etapa que falló (baja cardinalidad: "sparse" | "rerank").
    """
    if not _prometheus_available:
        return
    if _retrieval_fallback_total:
        _retrieval_fallback_total.labels(stage=stage).inc()


def record_connector_file_created(count: int = 1) -> None:
    """Cuenta archivos creados (nuevos) por sync de conectores."""
    if not _prometheus_available:
        return
    if _connector_files_created_total:
        _connector_files_created_total.inc(count)


def record_connector_file_updated(count: int = 1) -> None:
    """Cuenta archivos actualizados (re-ingestados) por sync de conectores."""
    if not _prometheus_available:
        return
    if _connector_files_updated_total:
        _connector_files_updated_total.inc(count)


def record_connector_file_skipped_unchanged(count: int = 1) -> None:
    """Cuenta archivos omitidos (sin cambios) por sync de conectores."""
    if not _prometheus_available:
        return
    if _connector_files_skipped_unchanged_total:
        _connector_files_skipped_unchanged_total.inc(count)


# -----------------------------------------------------------------------------
# Helpers internos
# -----------------------------------------------------------------------------


def _normalize_endpoint(path: str) -> str:
    """Normaliza paths para evitar cardinalidad alta.

    Reemplaza UUIDs e IDs numéricos por `{id}`.
    """
    # Workspace IDs (evita cardinalidad alta en rutas workspace-scoped)
    path = re.sub(r"/workspaces/[^/]+", "/workspaces/{workspace_id}", path)
    # UUIDs
    path = re.sub(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        "{id}",
        path,
        flags=re.IGNORECASE,
    )
    # IDs numéricos
    path = re.sub(r"/\d+", "/{id}", path)
    return path


def _status_bucket(code: int) -> str:
    """Agrupa status code para baja cardinalidad."""
    if 200 <= code < 300:
        return "2xx"
    if 400 <= code < 500:
        return "4xx"
    if 500 <= code < 600:
        return "5xx"
    return "other"


# -----------------------------------------------------------------------------
# Exposición del endpoint /metrics
# -----------------------------------------------------------------------------


def get_metrics_response() -> tuple[bytes, str]:
    """Genera el body y content-type para /metrics."""
    if not _prometheus_available:
        return b"# prometheus_client no instalado\n", "text/plain"
    return generate_latest(_registry), CONTENT_TYPE_LATEST


def is_prometheus_available() -> bool:
    """Indica si prometheus_client está instalado."""
    return _prometheus_available
