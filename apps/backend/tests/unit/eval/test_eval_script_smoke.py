"""
Name: Eval Script Smoke Tests

Responsibilities:
  - Verify eval_rag.run_evaluation produces a valid report.
  - Verify report structure has expected fields and sane values.
  - Verify deterministic output (same dataset → same scores).
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_DATASET_DIR = Path(__file__).resolve().parents[3] / "eval" / "dataset"


@pytest.fixture(scope="module")
def eval_report():
    """Run evaluation once and share across tests in this module."""
    import os

    os.environ.setdefault("FAKE_EMBEDDINGS", "1")
    os.environ.setdefault("FAKE_LLM", "1")
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("DATABASE_URL", "postgresql://x:x@localhost/x")
    os.environ.setdefault("JWT_SECRET", "eval-harness")
    os.environ.setdefault("GOOGLE_API_KEY", "eval-harness-fake")

    # Import here to avoid polluting other test modules with env side-effects
    from scripts.eval_rag import run_evaluation

    return run_evaluation(
        corpus_path=_DATASET_DIR / "corpus.jsonl",
        queries_path=_DATASET_DIR / "golden_queries.jsonl",
        top_k=5,
        verbose=False,
    )


class TestEvalScriptSmoke:
    """Smoke tests: the eval script runs and produces a valid report."""

    def test_report_has_metrics(self, eval_report):
        assert eval_report.metrics, "metrics dict should not be empty"
        assert "mrr" in eval_report.metrics
        assert "hit@1" in eval_report.metrics
        assert "recall@5" in eval_report.metrics
        assert "ndcg@5" in eval_report.metrics

    def test_metrics_are_in_range(self, eval_report):
        for name, value in eval_report.metrics.items():
            assert 0.0 <= value <= 1.0, f"{name}={value} out of [0, 1] range"

    def test_corpus_and_query_counts(self, eval_report):
        assert eval_report.corpus_size == 15
        assert eval_report.query_count == 30

    def test_per_query_has_all_entries(self, eval_report):
        assert len(eval_report.per_query) == 30
        for entry in eval_report.per_query:
            assert "query_id" in entry
            assert "retrieved_docs" in entry
            assert "relevant_docs" in entry

    def test_embedding_model_recorded(self, eval_report):
        assert eval_report.embedding_model == "fake-embedding-v1"

    def test_top_k_respected(self, eval_report):
        assert eval_report.top_k == 5
        for entry in eval_report.per_query:
            assert len(entry["retrieved_docs"]) <= 5

    def test_deterministic_output(self, eval_report):
        """Running twice with same data produces identical scores."""
        from scripts.eval_rag import run_evaluation

        report2 = run_evaluation(
            corpus_path=_DATASET_DIR / "corpus.jsonl",
            queries_path=_DATASET_DIR / "golden_queries.jsonl",
            top_k=5,
            verbose=False,
        )
        assert eval_report.metrics == report2.metrics

    def test_report_serializable_to_json(self, eval_report):
        """Report data can be serialized to JSON without errors."""
        report_dict = {
            "metrics": eval_report.metrics,
            "per_query": eval_report.per_query,
            "corpus_size": eval_report.corpus_size,
        }
        output = json.dumps(report_dict)
        parsed = json.loads(output)
        assert parsed["metrics"] == eval_report.metrics
