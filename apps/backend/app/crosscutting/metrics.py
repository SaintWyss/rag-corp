"""
Name: Prometheus Metrics

Responsibilities:
  - Define and expose Prometheus metrics
  - Provide /metrics endpoint handler
  - Record request latency, count, and stage timings

Collaborators:
  - middleware.py: Records request metrics
  - application/use_cases: Records stage timings (embed, retrieve, llm)

Constraints:
  - Low cardinality labels only (endpoint, method, status - NOT user_id)
  - Lazy initialization (don't fail if prometheus_client not installed)

Notes:
  - Metrics are global singletons (Prometheus requirement)
  - Histogram buckets chosen for typical latencies
  - prometheus_client is optional dependency
"""

import re
from typing import Optional

# R: Lazy import to make prometheus_client optional
_prometheus_available = False
_registry = None

try:
    from prometheus_client import (
        Counter,
        Histogram,
        CollectorRegistry,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )

    _prometheus_available = True
    _registry = CollectorRegistry()
except ImportError:
    pass


# R: Request metrics (populated if prometheus available)
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


def _init_metrics() -> None:
    """R: Initialize Prometheus metrics (called once)."""
    global _requests_total, _request_latency
    global _embed_latency, _retrieve_latency, _llm_latency
    global _embedding_cache_hits, _embedding_cache_misses
    global _worker_processed_total, _worker_failed_total, _worker_duration
    global _policy_refusal_total, _prompt_injection_detected_total
    global _cross_scope_block_total, _answer_without_sources_total
    global _sources_returned_count

    if not _prometheus_available or _requests_total is not None:
        return

    # R: Request counter with endpoint and status labels
    _requests_total = Counter(
        "rag_requests_total",
        "Total HTTP requests",
        ["endpoint", "method", "status"],
        registry=_registry,
    )

    # R: Request latency histogram (seconds)
    # Buckets: 10ms, 25ms, 50ms, 100ms, 250ms, 500ms, 1s, 2.5s, 5s, 10s
    _request_latency = Histogram(
        "rag_request_latency_seconds",
        "HTTP request latency in seconds",
        ["endpoint", "method"],
        buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        registry=_registry,
    )

    # R: Stage latency histograms (for RAG pipeline)
    _embed_latency = Histogram(
        "rag_embed_latency_seconds",
        "Embedding generation latency in seconds",
        buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
        registry=_registry,
    )

    _retrieve_latency = Histogram(
        "rag_retrieve_latency_seconds",
        "Chunk retrieval latency in seconds",
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
        registry=_registry,
    )

    _llm_latency = Histogram(
        "rag_llm_latency_seconds",
        "LLM generation latency in seconds",
        buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
        registry=_registry,
    )

    _embedding_cache_hits = Counter(
        "rag_embedding_cache_hit_total",
        "Embedding cache hits",
        ["kind"],
        registry=_registry,
    )

    _embedding_cache_misses = Counter(
        "rag_embedding_cache_miss_total",
        "Embedding cache misses",
        ["kind"],
        registry=_registry,
    )

    _worker_processed_total = Counter(
        "rag_worker_processed_total",
        "Total documents processed by worker",
        ["status"],
        registry=_registry,
    )

    _worker_failed_total = Counter(
        "rag_worker_failed_total",
        "Total documents failed in worker",
        registry=_registry,
    )

    _worker_duration = Histogram(
        "rag_worker_duration_seconds",
        "Worker document processing duration in seconds",
        buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
        registry=_registry,
    )

    _policy_refusal_total = Counter(
        "rag_policy_refusal_total",
        "Total policy refusals",
        ["reason"],
        registry=_registry,
    )

    _prompt_injection_detected_total = Counter(
        "rag_prompt_injection_detected_total",
        "Prompt injection detections by pattern",
        ["pattern"],
        registry=_registry,
    )

    _cross_scope_block_total = Counter(
        "rag_cross_scope_block_total",
        "Cross-scope or missing scope blocks",
        registry=_registry,
    )

    _answer_without_sources_total = Counter(
        "rag_answer_without_sources_total",
        "Answers returned without sources section",
        registry=_registry,
    )

    _sources_returned_count = Histogram(
        "rag_sources_returned_count",
        "Number of sources returned in RAG responses",
        buckets=(0, 1, 2, 3, 5, 8, 13, 21),
        registry=_registry,
    )


# R: Initialize on module load
_init_metrics()


def record_request_metrics(
    endpoint: str,
    method: str,
    status_code: int,
    latency_seconds: float,
) -> None:
    """
    R: Record HTTP request metrics.

    Args:
        endpoint: Request path (e.g., "/v1/ask")
        method: HTTP method (e.g., "POST")
        status_code: Response status code
        latency_seconds: Request duration in seconds
    """
    if not _prometheus_available:
        return

    # R: Normalize endpoint to avoid high cardinality
    # /v1/documents/123 -> /v1/documents/{id}
    normalized = _normalize_endpoint(endpoint)
    status_bucket = _status_bucket(status_code)

    if _requests_total:
        _requests_total.labels(
            endpoint=normalized,
            method=method,
            status=status_bucket,
        ).inc()

    if _request_latency:
        _request_latency.labels(
            endpoint=normalized,
            method=method,
        ).observe(latency_seconds)


def record_stage_metrics(
    embed_seconds: Optional[float] = None,
    retrieve_seconds: Optional[float] = None,
    llm_seconds: Optional[float] = None,
) -> None:
    """
    R: Record RAG pipeline stage metrics.

    Args:
        embed_seconds: Time spent generating embeddings
        retrieve_seconds: Time spent retrieving chunks
        llm_seconds: Time spent on LLM generation
    """
    if not _prometheus_available:
        return

    if embed_seconds is not None and _embed_latency:
        _embed_latency.observe(embed_seconds)

    if retrieve_seconds is not None and _retrieve_latency:
        _retrieve_latency.observe(retrieve_seconds)

    if llm_seconds is not None and _llm_latency:
        _llm_latency.observe(llm_seconds)


def record_embedding_cache_hit(count: int = 1, kind: str = "query") -> None:
    """R: Record embedding cache hit count."""
    if not _prometheus_available:
        return
    if _embedding_cache_hits:
        _embedding_cache_hits.labels(kind=kind).inc(count)


def record_embedding_cache_miss(count: int = 1, kind: str = "query") -> None:
    """R: Record embedding cache miss count."""
    if not _prometheus_available:
        return
    if _embedding_cache_misses:
        _embedding_cache_misses.labels(kind=kind).inc(count)


def record_worker_processed(status: str) -> None:
    """R: Record worker processed document status."""
    if not _prometheus_available:
        return
    if _worker_processed_total:
        _worker_processed_total.labels(status=status).inc()


def record_worker_failed(count: int = 1) -> None:
    """R: Record worker failed document count."""
    if not _prometheus_available:
        return
    if _worker_failed_total:
        _worker_failed_total.inc(count)


def observe_worker_duration(duration_seconds: float) -> None:
    """R: Record worker document processing duration."""
    if not _prometheus_available:
        return
    if _worker_duration:
        _worker_duration.observe(duration_seconds)


def record_policy_refusal(reason: str) -> None:
    """R: Record policy refusal with reason label."""
    if not _prometheus_available:
        return
    if _policy_refusal_total:
        _policy_refusal_total.labels(reason=reason).inc()


def record_prompt_injection_detected(pattern: str) -> None:
    """R: Record prompt injection detection by pattern slug."""
    if not _prometheus_available:
        return
    if _prompt_injection_detected_total:
        _prompt_injection_detected_total.labels(pattern=pattern).inc()


def record_cross_scope_block(count: int = 1) -> None:
    """R: Record cross-scope block count."""
    if not _prometheus_available:
        return
    if _cross_scope_block_total:
        _cross_scope_block_total.inc(count)


def record_answer_without_sources(count: int = 1) -> None:
    """R: Record answers without sources section."""
    if not _prometheus_available:
        return
    if _answer_without_sources_total:
        _answer_without_sources_total.inc(count)


def observe_sources_returned_count(count: int) -> None:
    """R: Observe number of sources returned."""
    if not _prometheus_available:
        return
    if _sources_returned_count:
        _sources_returned_count.observe(count)


def _normalize_endpoint(path: str) -> str:
    """
    R: Normalize endpoint path to prevent high cardinality.

    Replaces UUIDs and numeric IDs with placeholders.
    """
    # Replace UUIDs
    path = re.sub(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        "{id}",
        path,
        flags=re.IGNORECASE,
    )
    # Replace numeric IDs
    path = re.sub(r"/\d+", "/{id}", path)
    return path


def _status_bucket(code: int) -> str:
    """R: Bucket status code (2xx, 4xx, 5xx)."""
    if 200 <= code < 300:
        return "2xx"
    elif 400 <= code < 500:
        return "4xx"
    elif 500 <= code < 600:
        return "5xx"
    return "other"


def get_metrics_response() -> tuple[bytes, str]:
    """
    R: Generate Prometheus metrics response.

    Returns:
        Tuple of (body_bytes, content_type)
    """
    if not _prometheus_available:
        return b"# prometheus_client not installed\n", "text/plain"

    return generate_latest(_registry), CONTENT_TYPE_LATEST


def is_prometheus_available() -> bool:
    """R: Check if prometheus_client is installed."""
    return _prometheus_available
