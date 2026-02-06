"""
Name: RAG Evaluation Metrics

Responsibilities:
  - Compute standard IR evaluation metrics from ranked retrieval results.
  - All functions are pure (no IO, no side-effects) — easy to test.

Metrics:
  - MRR  (Mean Reciprocal Rank)
  - Recall@k
  - Hit@1 (aka Precision@1 / Success@1)
  - NDCG@k (Normalized Discounted Cumulative Gain)

Conventions:
  - ``retrieved``: ordered list of doc/chunk identifiers (best first).
  - ``relevant``: set of identifiers considered relevant for a query.
  - All functions accept parallel lists (one entry per query).
"""

from __future__ import annotations

import math
from typing import List, Set

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate_parallel(
    retrieved: List[List[str]],
    relevant: List[Set[str]],
) -> None:
    """Raise ValueError if inputs are mismatched."""
    if len(retrieved) != len(relevant):
        raise ValueError(
            f"retrieved ({len(retrieved)}) and relevant ({len(relevant)}) "
            "must have the same length"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def mean_reciprocal_rank(
    retrieved: List[List[str]],
    relevant: List[Set[str]],
) -> float:
    """Mean Reciprocal Rank (MRR).

    For each query the reciprocal rank is 1/rank of the *first* relevant item
    in the retrieved list.  If no relevant item is found, the reciprocal rank
    is 0.  The MRR is the mean across all queries.

    Returns 0.0 when *retrieved* is empty.
    """
    _validate_parallel(retrieved, relevant)
    if not retrieved:
        return 0.0

    total = 0.0
    for ret, rel in zip(retrieved, relevant):
        for rank, doc_id in enumerate(ret, start=1):
            if doc_id in rel:
                total += 1.0 / rank
                break
    return total / len(retrieved)


def recall_at_k(
    retrieved: List[List[str]],
    relevant: List[Set[str]],
    k: int,
) -> float:
    """Recall@k — fraction of relevant docs found in the top-k results.

    Averaged across all queries.  Queries with an empty relevant set are
    counted as recall = 0 (no relevant docs to recall).

    Returns 0.0 when *retrieved* is empty.
    """
    _validate_parallel(retrieved, relevant)
    if k <= 0:
        raise ValueError("k must be > 0")
    if not retrieved:
        return 0.0

    total = 0.0
    for ret, rel in zip(retrieved, relevant):
        top_k = set(ret[:k])
        if rel:
            total += len(top_k & rel) / len(rel)
    return total / len(retrieved)


def hit_at_1(
    retrieved: List[List[str]],
    relevant: List[Set[str]],
) -> float:
    """Hit@1 (Success@1) — fraction of queries where the top result is relevant.

    Returns 0.0 when *retrieved* is empty.
    """
    _validate_parallel(retrieved, relevant)
    if not retrieved:
        return 0.0

    hits = sum(1 for ret, rel in zip(retrieved, relevant) if ret and ret[0] in rel)
    return hits / len(retrieved)


def ndcg_at_k(
    retrieved: List[List[str]],
    relevant: List[Set[str]],
    k: int,
) -> float:
    """NDCG@k — Normalized Discounted Cumulative Gain at k.

    Uses binary relevance (1 if in relevant set, 0 otherwise).
    The ideal ranking places all relevant docs at the top.

    Returns 0.0 when *retrieved* is empty.
    """
    _validate_parallel(retrieved, relevant)
    if k <= 0:
        raise ValueError("k must be > 0")
    if not retrieved:
        return 0.0

    def _dcg(ranked: List[str], rel_set: Set[str], limit: int) -> float:
        score = 0.0
        for i, doc_id in enumerate(ranked[:limit]):
            if doc_id in rel_set:
                score += 1.0 / math.log2(i + 2)  # i+2 because rank starts at 1
        return score

    total = 0.0
    for ret, rel in zip(retrieved, relevant):
        dcg = _dcg(ret, rel, k)
        # Ideal: all relevant docs at top positions
        ideal_count = min(len(rel), k)
        idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_count))
        if idcg > 0:
            total += dcg / idcg
    return total / len(retrieved)
