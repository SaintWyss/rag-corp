"""
Unit tests for RAG security metrics.
"""

import pytest

from app.crosscutting.metrics import (
    get_metrics_response,
    is_prometheus_available,
    observe_sources_returned_count,
    record_answer_without_sources,
    record_cross_scope_block,
    record_policy_refusal,
    record_prompt_injection_detected,
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
