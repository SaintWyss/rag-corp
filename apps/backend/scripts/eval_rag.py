#!/usr/bin/env python3
"""
Name: RAG Evaluation Script

Responsibilities:
  - Load golden dataset (corpus + queries with relevance judgments).
  - Embed corpus chunks and queries using the configured EmbeddingService.
  - Perform cosine-similarity retrieval in-memory (no DB required).
  - Calculate MRR, Recall@k, Hit@1, NDCG@k.
  - Export a JSON report to stdout or file.

Usage:
    python scripts/eval_rag.py                     # defaults
    python scripts/eval_rag.py --top-k 10          # custom k
    python scripts/eval_rag.py --out report.json   # write to file
    python scripts/eval_rag.py --verbose            # show per-query results

Environment:
    FAKE_EMBEDDINGS=1  (default) — deterministic, no API key needed
    FAKE_EMBEDDINGS=0            — uses real embeddings (requires GOOGLE_API_KEY)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

# Ensure fake services by default (can be overridden by env)
os.environ.setdefault("FAKE_EMBEDDINGS", "1")
os.environ.setdefault("FAKE_LLM", "1")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "postgresql://x:x@localhost/x")
os.environ.setdefault("JWT_SECRET", "eval-harness")
os.environ.setdefault("GOOGLE_API_KEY", "eval-harness-fake")

_EVAL_ROOT = _BACKEND_ROOT / "eval"
_DATASET_DIR = _EVAL_ROOT / "dataset"

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CorpusDoc:
    doc_id: str
    title: str
    content: str


@dataclass
class GoldenQuery:
    query_id: str
    query: str
    relevant_docs: List[str]
    category: str = ""


@dataclass
class IndexedChunk:
    """A chunk stored in the in-memory index."""

    doc_id: str
    chunk_index: int
    content: str
    embedding: List[float]


@dataclass
class QueryResult:
    """Result for a single evaluation query."""

    query_id: str
    query: str
    category: str
    relevant_docs: List[str]
    retrieved_docs: List[str]
    hit_at_1: bool
    reciprocal_rank: float
    recall_at_k: float


@dataclass
class EvalReport:
    """Full evaluation report."""

    timestamp: str = ""
    embedding_model: str = ""
    corpus_size: int = 0
    query_count: int = 0
    top_k: int = 5
    metrics: Dict[str, float] = field(default_factory=dict)
    per_query: List[Dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------


def load_corpus(path: Path) -> List[CorpusDoc]:
    docs = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            docs.append(
                CorpusDoc(
                    doc_id=obj["doc_id"],
                    title=obj["title"],
                    content=obj["content"],
                )
            )
    return docs


def load_queries(path: Path) -> List[GoldenQuery]:
    queries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            queries.append(
                GoldenQuery(
                    query_id=obj["query_id"],
                    query=obj["query"],
                    relevant_docs=obj["relevant_docs"],
                    category=obj.get("category", ""),
                )
            )
    return queries


# ---------------------------------------------------------------------------
# In-memory vector index (cosine similarity)
# ---------------------------------------------------------------------------


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class InMemoryVectorIndex:
    """Minimal vector index for evaluation purposes."""

    def __init__(self) -> None:
        self._chunks: List[IndexedChunk] = []

    def add(self, chunk: IndexedChunk) -> None:
        self._chunks.append(chunk)

    def search(
        self, query_embedding: List[float], top_k: int
    ) -> List[Tuple[IndexedChunk, float]]:
        scored = [
            (chunk, _cosine_similarity(query_embedding, chunk.embedding))
            for chunk in self._chunks
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    @property
    def size(self) -> int:
        return len(self._chunks)


# ---------------------------------------------------------------------------
# Chunking (simple split for eval — mirrors SimpleTextChunker logic)
# ---------------------------------------------------------------------------


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


# ---------------------------------------------------------------------------
# Evaluation runner
# ---------------------------------------------------------------------------


def run_evaluation(
    corpus_path: Path,
    queries_path: Path,
    top_k: int = 5,
    verbose: bool = False,
) -> EvalReport:
    """Run the full evaluation pipeline."""
    from app.infrastructure.services import FakeEmbeddingService

    # 1. Load dataset
    corpus = load_corpus(corpus_path)
    queries = load_queries(queries_path)

    if verbose:
        print(
            f"Loaded {len(corpus)} documents, {len(queries)} queries", file=sys.stderr
        )

    # 2. Initialize embedding service
    embed_svc = FakeEmbeddingService()

    # 3. Build in-memory index
    index = InMemoryVectorIndex()
    for doc in corpus:
        text_chunks = _chunk_text(doc.content)
        for i, chunk_text in enumerate(text_chunks):
            embedding = embed_svc.embed_query(chunk_text)
            index.add(
                IndexedChunk(
                    doc_id=doc.doc_id,
                    chunk_index=i,
                    content=chunk_text,
                    embedding=embedding,
                )
            )

    if verbose:
        print(f"Indexed {index.size} chunks", file=sys.stderr)

    # 4. Run queries and collect results
    all_retrieved: List[List[str]] = []
    all_relevant: List[Set[str]] = []
    per_query_results: List[QueryResult] = []

    for gq in queries:
        query_embedding = embed_svc.embed_query(gq.query)
        results = index.search(query_embedding, top_k=top_k)

        # Deduplicate by doc_id preserving rank order
        seen = set()
        retrieved_doc_ids: List[str] = []
        for chunk, score in results:
            if chunk.doc_id not in seen:
                seen.add(chunk.doc_id)
                retrieved_doc_ids.append(chunk.doc_id)

        relevant_set = set(gq.relevant_docs)
        all_retrieved.append(retrieved_doc_ids)
        all_relevant.append(relevant_set)

        # Per-query metrics
        _hit = bool(retrieved_doc_ids and retrieved_doc_ids[0] in relevant_set)
        _rr = 0.0
        for rank, did in enumerate(retrieved_doc_ids, start=1):
            if did in relevant_set:
                _rr = 1.0 / rank
                break
        _found = set(retrieved_doc_ids) & relevant_set
        _recall = len(_found) / len(relevant_set) if relevant_set else 0.0

        qr = QueryResult(
            query_id=gq.query_id,
            query=gq.query,
            category=gq.category,
            relevant_docs=gq.relevant_docs,
            retrieved_docs=retrieved_doc_ids,
            hit_at_1=_hit,
            reciprocal_rank=_rr,
            recall_at_k=_recall,
        )
        per_query_results.append(qr)

        if verbose:
            status = "HIT" if _hit else "MISS"
            print(
                f"  [{status}] {gq.query_id}: {gq.query[:50]}... "
                f"→ {retrieved_doc_ids[:3]}",
                file=sys.stderr,
            )

    # 5. Calculate aggregate metrics
    from eval.metrics import hit_at_1 as calc_hit_at_1
    from eval.metrics import mean_reciprocal_rank, ndcg_at_k
    from eval.metrics import recall_at_k as calc_recall_at_k

    mrr = mean_reciprocal_rank(all_retrieved, all_relevant)
    recall = calc_recall_at_k(all_retrieved, all_relevant, k=top_k)
    hit1 = calc_hit_at_1(all_retrieved, all_relevant)
    ndcg = ndcg_at_k(all_retrieved, all_relevant, k=top_k)

    # 6. Build report
    import datetime as dt

    report = EvalReport(
        timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),
        embedding_model=embed_svc.model_id,
        corpus_size=len(corpus),
        query_count=len(queries),
        top_k=top_k,
        metrics={
            "mrr": round(mrr, 4),
            f"recall@{top_k}": round(recall, 4),
            "hit@1": round(hit1, 4),
            f"ndcg@{top_k}": round(ndcg, 4),
        },
        per_query=[
            {
                "query_id": qr.query_id,
                "query": qr.query,
                "category": qr.category,
                "relevant_docs": qr.relevant_docs,
                "retrieved_docs": qr.retrieved_docs,
                "hit_at_1": qr.hit_at_1,
                "reciprocal_rank": round(qr.reciprocal_rank, 4),
                "recall_at_k": round(qr.recall_at_k, 4),
            }
            for qr in per_query_results
        ],
    )
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RAG retrieval evaluation harness",
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=_DATASET_DIR / "corpus.jsonl",
        help="Path to corpus JSONL file",
    )
    parser.add_argument(
        "--queries",
        type=Path,
        default=_DATASET_DIR / "golden_queries.jsonl",
        help="Path to golden queries JSONL file",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of results to retrieve per query (default: 5)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output file for JSON report (default: stdout)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show per-query results on stderr",
    )
    args = parser.parse_args()

    t0 = time.perf_counter()
    report = run_evaluation(
        corpus_path=args.corpus,
        queries_path=args.queries,
        top_k=args.top_k,
        verbose=args.verbose,
    )
    elapsed = time.perf_counter() - t0

    report_dict = {
        "timestamp": report.timestamp,
        "embedding_model": report.embedding_model,
        "corpus_size": report.corpus_size,
        "query_count": report.query_count,
        "top_k": report.top_k,
        "elapsed_seconds": round(elapsed, 2),
        "metrics": report.metrics,
        "per_query": report.per_query,
    }

    output = json.dumps(report_dict, indent=2, ensure_ascii=False)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
        print(f"Report written to {args.out}", file=sys.stderr)
    else:
        print(output)

    # Summary on stderr
    print(f"\n{'='*50}", file=sys.stderr)
    print("  RAG Evaluation Report", file=sys.stderr)
    print(f"  Model: {report.embedding_model}", file=sys.stderr)
    print(
        f"  Corpus: {report.corpus_size} docs | Queries: {report.query_count}",
        file=sys.stderr,
    )
    print(f"  top_k: {report.top_k}", file=sys.stderr)
    print(f"{'='*50}", file=sys.stderr)
    for name, value in report.metrics.items():
        print(f"  {name:>12s}: {value:.4f}", file=sys.stderr)
    print(f"  {'elapsed':>12s}: {elapsed:.2f}s", file=sys.stderr)
    print(f"{'='*50}", file=sys.stderr)


if __name__ == "__main__":
    main()
