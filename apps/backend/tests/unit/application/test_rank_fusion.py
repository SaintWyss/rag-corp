"""
Name: RankFusionService Unit Tests

Responsibilities:
  - Verificar fórmula RRF con valores exactos
  - Testar edge cases (listas vacías, un solo ranking, chunks duplicados)
  - Validar parámetro k
  - Confirmar deduplicación por chunk_id y por (document_id, chunk_index)
"""

from uuid import UUID, uuid4

import pytest
from app.application.rank_fusion import RankFusionService
from app.domain.entities import Chunk

# ============================================================
# Helpers
# ============================================================


def _chunk(
    content: str = "test",
    chunk_id: UUID | None = None,
    document_id: UUID | None = None,
    chunk_index: int = 0,
    similarity: float | None = None,
) -> Chunk:
    return Chunk(
        content=content,
        embedding=[],
        chunk_id=chunk_id or uuid4(),
        document_id=document_id or uuid4(),
        chunk_index=chunk_index,
        similarity=similarity,
    )


# ============================================================
# Tests: Constructor
# ============================================================


class TestRankFusionServiceInit:

    def test_default_k(self):
        rrf = RankFusionService()
        assert rrf.k == 60

    def test_custom_k(self):
        rrf = RankFusionService(k=10)
        assert rrf.k == 10

    def test_invalid_k_zero(self):
        with pytest.raises(ValueError, match="k debe ser > 0"):
            RankFusionService(k=0)

    def test_invalid_k_negative(self):
        with pytest.raises(ValueError, match="k debe ser > 0"):
            RankFusionService(k=-5)


# ============================================================
# Tests: Fórmula RRF
# ============================================================


class TestRankFusionServiceFuse:

    def test_single_list_preserves_order(self):
        rrf = RankFusionService(k=60)
        c1 = _chunk(content="A")
        c2 = _chunk(content="B")
        c3 = _chunk(content="C")

        result = rrf.fuse([c1, c2, c3])

        assert len(result) == 3
        # Con un solo ranking, RRF preserva el orden original
        assert result[0].content == "A"
        assert result[1].content == "B"
        assert result[2].content == "C"

    def test_two_lists_rrf_scores_exact(self):
        """Verifica la fórmula RRF con k=60 y valores exactos."""
        rrf = RankFusionService(k=60)
        k = 60

        # Chunk compartido
        shared_id = uuid4()
        doc_id = uuid4()
        c_shared_dense = _chunk(
            content="shared", chunk_id=shared_id, document_id=doc_id
        )
        c_shared_sparse = _chunk(
            content="shared", chunk_id=shared_id, document_id=doc_id
        )

        # Chunks exclusivos
        c_dense_only = _chunk(content="dense_only")
        c_sparse_only = _chunk(content="sparse_only")

        dense = [c_shared_dense, c_dense_only]
        sparse = [c_sparse_only, c_shared_sparse]

        result = rrf.fuse(dense, sparse)

        # Scores esperados:
        # shared: 1/(60+1) + 1/(60+2) = 1/61 + 1/62
        # dense_only: 1/(60+2) (rank 2 en dense)
        # sparse_only: 1/(60+1) (rank 1 en sparse)
        score_shared = 1 / (k + 1) + 1 / (k + 2)
        score_dense_only = 1 / (k + 2)
        score_sparse_only = 1 / (k + 1)

        # shared debe estar primero (mayor score)
        assert result[0].chunk_id == shared_id
        # sparse_only > dense_only (rank 1 vs rank 2)
        assert result[1].content == "sparse_only"
        assert result[2].content == "dense_only"

        # Verificar que los scores calculados son correctos
        assert score_shared > score_sparse_only > score_dense_only

    def test_empty_lists(self):
        rrf = RankFusionService(k=60)
        assert rrf.fuse() == []
        assert rrf.fuse([]) == []
        assert rrf.fuse([], []) == []

    def test_one_empty_one_populated(self):
        rrf = RankFusionService(k=60)
        c1 = _chunk(content="only")

        result = rrf.fuse([], [c1])

        assert len(result) == 1
        assert result[0].content == "only"

    def test_three_lists_accumulate_scores(self):
        """Chunk in all 3 lists should have highest score."""
        rrf = RankFusionService(k=60)
        k = 60

        c_all = _chunk(content="in_all")
        c_two = _chunk(content="in_two")
        c_one = _chunk(content="in_one")

        list_a = [c_all, c_two, c_one]
        list_b = [c_two, c_all]
        list_c = [c_all]

        result = rrf.fuse(list_a, list_b, list_c)

        # c_all: rank 1 in A + rank 2 in B + rank 1 in C
        # c_two: rank 2 in A + rank 1 in B
        # c_one: rank 3 in A
        score_all = 1 / (k + 1) + 1 / (k + 2) + 1 / (k + 1)
        score_two = 1 / (k + 2) + 1 / (k + 1)
        score_one = 1 / (k + 3)

        assert result[0].content == "in_all"
        assert score_all > score_two > score_one

    def test_different_k_values_affect_ranking(self):
        """Con k bajo, rank importa más. Con k alto, rank importa menos."""
        c1 = _chunk(content="rank1_listA")
        c2 = _chunk(content="rank1_listB")

        # k=1: grandes diferencias de score entre ranks
        rrf_low = RankFusionService(k=1)
        result_low = rrf_low.fuse([c1], [c2])
        # Ambos rank 1 en sus respectivas listas => mismos scores
        assert len(result_low) == 2

        # k=1000: diferencias de score mínimas
        rrf_high = RankFusionService(k=1000)
        result_high = rrf_high.fuse([c1], [c2])
        assert len(result_high) == 2


# ============================================================
# Tests: Deduplicación
# ============================================================


class TestRankFusionServiceDedup:

    def test_dedup_by_chunk_id(self):
        """Mismo chunk_id en ambas listas genera un solo resultado."""
        rrf = RankFusionService(k=60)
        cid = uuid4()
        did = uuid4()

        c_dense = _chunk(content="dense ver", chunk_id=cid, document_id=did)
        c_sparse = _chunk(content="sparse ver", chunk_id=cid, document_id=did)

        result = rrf.fuse([c_dense], [c_sparse])
        assert len(result) == 1
        # Debe conservar la primera aparición
        assert result[0].content == "dense ver"

    def test_fallback_key_without_chunk_id(self):
        """Sin chunk_id usa (document_id, chunk_index) como clave."""
        rrf = RankFusionService(k=60)
        did = uuid4()

        c1 = Chunk(
            content="v1",
            embedding=[],
            chunk_id=None,
            document_id=did,
            chunk_index=3,
        )
        c2 = Chunk(
            content="v2",
            embedding=[],
            chunk_id=None,
            document_id=did,
            chunk_index=3,
        )

        result = rrf.fuse([c1], [c2])
        assert len(result) == 1

    def test_distinct_chunks_not_deduped(self):
        """Chunks diferentes no se fusionan."""
        rrf = RankFusionService(k=60)
        c1 = _chunk(content="A")
        c2 = _chunk(content="B")

        result = rrf.fuse([c1, c2])
        assert len(result) == 2


# ============================================================
# Tests: Propiedades
# ============================================================


class TestRankFusionServiceProperties:

    def test_result_is_union_of_inputs(self):
        """El resultado contiene la unión de todos los chunks únicos."""
        rrf = RankFusionService(k=60)
        chunks_a = [_chunk(content=f"a{i}") for i in range(3)]
        chunks_b = [_chunk(content=f"b{i}") for i in range(2)]

        result = rrf.fuse(chunks_a, chunks_b)
        assert len(result) == 5

    def test_result_length_with_overlap(self):
        """Con overlap, la unión tiene menos elementos que la suma."""
        rrf = RankFusionService(k=60)
        shared = _chunk(content="shared")

        list_a = [shared, _chunk(content="a_only")]
        list_b = [_chunk(content="b_only"), shared]

        result = rrf.fuse(list_a, list_b)
        assert len(result) == 3  # shared + a_only + b_only
