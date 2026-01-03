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


def _init_metrics() -> None:
    """R: Initialize Prometheus metrics (called once)."""
    global _requests_total, _request_latency
    global _embed_latency, _retrieve_latency, _llm_latency
    
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
