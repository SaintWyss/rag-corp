"""
Name: Evaluation Metrics Unit Tests

Responsibilities:
  - Verify MRR, Recall@k, Hit@1, NDCG@k produce correct scores
    for known inputs.
  - Verify edge cases: empty inputs, no relevant docs found, k > result size.
  - All tests are pure (no IO, no mocks needed).
"""

import math

import pytest
from eval.metrics import hit_at_1, mean_reciprocal_rank, ndcg_at_k, recall_at_k

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures — reusable retrieval scenarios
# ---------------------------------------------------------------------------


@pytest.fixture
def perfect_retrieval():
    """Every query's top-1 result is relevant."""
    retrieved = [["d1", "d2", "d3"], ["d4", "d5"]]
    relevant = [{"d1"}, {"d4"}]
    return retrieved, relevant


@pytest.fixture
def partial_retrieval():
    """Relevant doc is at rank 2 for query 1, rank 1 for query 2."""
    retrieved = [["d2", "d1", "d3"], ["d4", "d5"]]
    relevant = [{"d1"}, {"d4"}]
    return retrieved, relevant


@pytest.fixture
def no_relevant_found():
    """No relevant doc appears in any result list."""
    retrieved = [["d2", "d3"], ["d5", "d6"]]
    relevant = [{"d1"}, {"d4"}]
    return retrieved, relevant


# ---------------------------------------------------------------------------
# MRR
# ---------------------------------------------------------------------------


class TestMeanReciprocalRank:
    def test_perfect_retrieval(self, perfect_retrieval):
        ret, rel = perfect_retrieval
        assert mean_reciprocal_rank(ret, rel) == pytest.approx(1.0)

    def test_partial_retrieval(self, partial_retrieval):
        ret, rel = partial_retrieval
        # query 1: rank 2 → 1/2, query 2: rank 1 → 1/1 → mean = 0.75
        assert mean_reciprocal_rank(ret, rel) == pytest.approx(0.75)

    def test_no_relevant_found(self, no_relevant_found):
        ret, rel = no_relevant_found
        assert mean_reciprocal_rank(ret, rel) == pytest.approx(0.0)

    def test_empty_input(self):
        assert mean_reciprocal_rank([], []) == pytest.approx(0.0)

    def test_single_query_rank_3(self):
        ret = [["a", "b", "c", "d"]]
        rel = [{"c"}]
        assert mean_reciprocal_rank(ret, rel) == pytest.approx(1.0 / 3)

    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError, match="same length"):
            mean_reciprocal_rank([["a"]], [{"a"}, {"b"}])


# ---------------------------------------------------------------------------
# Recall@k
# ---------------------------------------------------------------------------


class TestRecallAtK:
    def test_perfect_at_k1(self, perfect_retrieval):
        ret, rel = perfect_retrieval
        assert recall_at_k(ret, rel, k=1) == pytest.approx(1.0)

    def test_partial_at_k1(self, partial_retrieval):
        ret, rel = partial_retrieval
        # query 1: top-1 is d2, not relevant → recall 0; query 2: top-1 is d4 → recall 1
        assert recall_at_k(ret, rel, k=1) == pytest.approx(0.5)

    def test_partial_at_k3(self, partial_retrieval):
        ret, rel = partial_retrieval
        # query 1: d1 is in top-3 → recall 1; query 2: d4 in top-2 → recall 1
        assert recall_at_k(ret, rel, k=3) == pytest.approx(1.0)

    def test_no_relevant_at_k5(self, no_relevant_found):
        ret, rel = no_relevant_found
        assert recall_at_k(ret, rel, k=5) == pytest.approx(0.0)

    def test_multiple_relevant_docs(self):
        ret = [["a", "b", "c", "d", "e"]]
        rel = [{"a", "c", "e"}]
        # k=3: found a and c → 2/3
        assert recall_at_k(ret, rel, k=3) == pytest.approx(2.0 / 3)
        # k=5: found a, c, e → 3/3
        assert recall_at_k(ret, rel, k=5) == pytest.approx(1.0)

    def test_empty_input(self):
        assert recall_at_k([], [], k=5) == pytest.approx(0.0)

    def test_k_zero_raises(self):
        with pytest.raises(ValueError, match="k must be > 0"):
            recall_at_k([["a"]], [{"a"}], k=0)

    def test_k_larger_than_results(self):
        """k > len(retrieved) should still work (take all available)."""
        ret = [["a", "b"]]
        rel = [{"b"}]
        assert recall_at_k(ret, rel, k=100) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Hit@1
# ---------------------------------------------------------------------------


class TestHitAt1:
    def test_perfect(self, perfect_retrieval):
        ret, rel = perfect_retrieval
        assert hit_at_1(ret, rel) == pytest.approx(1.0)

    def test_partial(self, partial_retrieval):
        ret, rel = partial_retrieval
        # query 1 miss, query 2 hit → 0.5
        assert hit_at_1(ret, rel) == pytest.approx(0.5)

    def test_none_hit(self, no_relevant_found):
        ret, rel = no_relevant_found
        assert hit_at_1(ret, rel) == pytest.approx(0.0)

    def test_empty_input(self):
        assert hit_at_1([], []) == pytest.approx(0.0)

    def test_empty_results_for_query(self):
        """A query with empty retrieval list counts as a miss."""
        ret = [[], ["d1"]]
        rel = [{"d1"}, {"d1"}]
        assert hit_at_1(ret, rel) == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# NDCG@k
# ---------------------------------------------------------------------------


class TestNdcgAtK:
    def test_perfect_single(self):
        """One relevant doc at rank 1 → NDCG = 1.0."""
        ret = [["a", "b", "c"]]
        rel = [{"a"}]
        assert ndcg_at_k(ret, rel, k=3) == pytest.approx(1.0)

    def test_relevant_at_rank2(self):
        """One relevant doc at rank 2."""
        ret = [["b", "a", "c"]]
        rel = [{"a"}]
        # DCG = 1/log2(3) ≈ 0.6309; IDCG = 1/log2(2) = 1.0 → NDCG ≈ 0.6309
        expected = (1.0 / math.log2(3)) / (1.0 / math.log2(2))
        assert ndcg_at_k(ret, rel, k=3) == pytest.approx(expected)

    def test_two_relevant_perfect_order(self):
        """Two relevant docs at ranks 1 and 2."""
        ret = [["a", "b", "c"]]
        rel = [{"a", "b"}]
        dcg = 1.0 / math.log2(2) + 1.0 / math.log2(3)
        idcg = dcg  # already perfect order
        assert ndcg_at_k(ret, rel, k=3) == pytest.approx(1.0)

    def test_no_relevant(self):
        ret = [["x", "y", "z"]]
        rel = [{"a"}]
        assert ndcg_at_k(ret, rel, k=3) == pytest.approx(0.0)

    def test_empty_input(self):
        assert ndcg_at_k([], [], k=5) == pytest.approx(0.0)

    def test_k_zero_raises(self):
        with pytest.raises(ValueError, match="k must be > 0"):
            ndcg_at_k([["a"]], [{"a"}], k=0)

    def test_averaged_across_queries(self):
        """NDCG averaged over 2 queries: one perfect, one at rank 2."""
        ret = [["a", "b"], ["c", "d"]]
        rel = [{"a"}, {"d"}]
        ndcg_q1 = 1.0  # relevant at rank 1
        ndcg_q2 = (1.0 / math.log2(3)) / (1.0 / math.log2(2))  # relevant at rank 2
        expected = (ndcg_q1 + ndcg_q2) / 2
        assert ndcg_at_k(ret, rel, k=3) == pytest.approx(expected)
