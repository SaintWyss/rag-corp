"""
===============================================================================
MÓDULO: Node Builder (Generación de nodos para 2-tier retrieval)
===============================================================================

Responsabilidades:
  - Agrupar chunks consecutivos en nodos (secciones).
  - Concatenar texto de chunks agrupados (truncado a max_chars).
  - Generar embeddings batch para los nodos resultantes.
  - Calcular span_start/span_end por nodo (rango de chunk_index).

Colaboradores:
  - domain.entities: Chunk, Node
  - domain.services: EmbeddingService (embed_batch)

Invariantes:
  - Función pura (sin IO directo, sin estado mutable).
  - Compatible con FakeEmbeddingService (sin API keys).
  - Si chunks es vacío → retorna lista vacía (no invoca embedding).
===============================================================================
"""

from __future__ import annotations

import logging
from typing import List
from uuid import UUID

from ..domain.entities import Chunk, Node
from ..domain.services import EmbeddingService

logger = logging.getLogger(__name__)


def build_nodes(
    document_id: UUID,
    workspace_id: UUID,
    chunks: List[Chunk],
    embedding_service: EmbeddingService,
    group_size: int = 5,
    max_chars: int = 2000,
) -> List[Node]:
    """
    Genera nodos (secciones) a partir de una lista de chunks.

    Parámetros:
      - document_id: ID del documento fuente.
      - workspace_id: ID del workspace (scope).
      - chunks: Lista de Chunk entities (deben tener chunk_index).
      - embedding_service: Servicio de embeddings (embed_batch).
      - group_size: Cantidad de chunks por nodo.
      - max_chars: Longitud máxima de node_text (truncado).

    Retorna:
      Lista de Node entities (sin node_id, se asigna al persistir).
    """
    if not chunks:
        return []

    # Ordenar por chunk_index para agrupamiento correcto
    sorted_chunks = sorted(
        chunks,
        key=lambda c: c.chunk_index if c.chunk_index is not None else 0,
    )

    # Agrupar en bloques de group_size
    groups: list[list[Chunk]] = []
    for i in range(0, len(sorted_chunks), group_size):
        groups.append(sorted_chunks[i : i + group_size])

    # Construir node_text y calcular spans
    node_texts: list[str] = []
    node_spans: list[tuple[int, int]] = []  # (span_start, span_end)

    for group in groups:
        text = " ".join(c.content for c in group)
        if len(text) > max_chars:
            text = text[:max_chars]
        node_texts.append(text)

        span_start = group[0].chunk_index if group[0].chunk_index is not None else 0
        span_end = group[-1].chunk_index if group[-1].chunk_index is not None else 0
        node_spans.append((span_start, span_end))

    # Embeddings batch (una sola llamada para eficiencia)
    embeddings = embedding_service.embed_batch(node_texts)

    # Construir entidades Node
    nodes: list[Node] = []
    for idx, (text, embedding, (span_start, span_end)) in enumerate(
        zip(node_texts, embeddings, node_spans)
    ):
        nodes.append(
            Node(
                node_text=text,
                embedding=embedding,
                workspace_id=workspace_id,
                document_id=document_id,
                node_index=idx,
                span_start=span_start,
                span_end=span_end,
            )
        )

    logger.info(
        "Node builder: nodes generated",
        extra={
            "document_id": str(document_id),
            "chunks": len(chunks),
            "nodes": len(nodes),
            "group_size": group_size,
        },
    )

    return nodes
