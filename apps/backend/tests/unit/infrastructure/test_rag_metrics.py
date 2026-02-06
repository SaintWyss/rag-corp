"""
Unit tests for RAG metrics (security + pipeline stages).
"""

import pytest
from app.crosscutting.metrics import (
    get_metrics_response,
    is_prometheus_available,
    observe_dense_latency,
    observe_fusion_latency,
    observe_rerank_latency,
    observe_sources_returned_count,
    observe_sparse_latency,
    record_answer_without_sources,
    record_cross_scope_block,
    record_policy_refusal,
    record_prompt_injection_detected,
    record_retrieval_fallback,
)

pytestmark = pytest.mark.unit


def test_rag_metrics_are_exposed():
    if not is_prometheus_available():
        pytest.skip("prometheus_client not available")

    record_policy_refusal("insufficient_evidence")
    record_prompt_injection_detected("system_prompt")
    record_cross_scope_block()
    record_answer_without_sources()
    observe_sources_returned_count(2)

    body, _ = get_metrics_response()
    payload = body.decode("utf-8")

    assert "rag_policy_refusal_total" in payload
    assert "rag_prompt_injection_detected_total" in payload
    assert "rag_cross_scope_block_total" in payload
    assert "rag_answer_without_sources_total" in payload
    assert "rag_sources_returned_count" in payload


def test_pipeline_stage_metrics_are_exposed():
    """New stage metrics appear in /metrics after recording."""
    if not is_prometheus_available():
        pytest.skip("prometheus_client not available")

    observe_dense_latency(0.012)
    observe_sparse_latency(0.008)
    observe_fusion_latency(0.001)
    observe_rerank_latency(0.045)
    record_retrieval_fallback("sparse")

    body, _ = get_metrics_response()
    payload = body.decode("utf-8")

    assert "rag_dense_latency_seconds" in payload
    assert "rag_sparse_latency_seconds" in payload
    assert "rag_fusion_latency_seconds" in payload
    assert "rag_rerank_latency_seconds" in payload
    assert "rag_retrieval_fallback_total" in payload
    assert 'stage="sparse"' in payload
