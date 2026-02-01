"""
===============================================================================
CRC CARD — infrastructure/text/chunker.py
===============================================================================

Componente:
  Chunking de texto (Strategy-friendly)

Responsabilidades:
  - Proveer chunking determinístico y robusto para ingesta.
  - Preferir cortes naturales (párrafos, saltos, oraciones) con overlap.
  - Exponer:
      * chunk_text(...) -> list[str] (compatibilidad)
      * chunk_fragments(...) -> list[ChunkFragment] (salida rica)
      * SimpleTextChunker (servicio)

Colaboradores:
  - infrastructure/text/models.py (ChunkFragment)

Decisiones senior:
  - Guard clauses + validación de parámetros (fail-fast).
  - Límite de chunks para evitar bombas de memoria.
  - Post-proceso: merge de “micro-chunks” finales cuando conviene.
===============================================================================
"""

from __future__ import annotations

from typing import Final

from .models import ChunkFragment

# Separadores en orden de prioridad (mejor a peor).
_SEPARATORS: Final[list[str]] = ["\n\n", "\n", ". ", "; ", ", ", " "]

# Guardrail: evita generar miles de chunks por inputs patológicos.
_DEFAULT_MAX_CHUNKS: Final[int] = 2000


def _find_best_split(text: str, target: int, window: int = 120) -> int:
    """
    Encuentra el mejor punto de corte cerca de `target`.

    Estrategia:
      - Buscar hacia atrás dentro de una ventana y elegir el último separador.
      - Si no encuentra nada, cortar exacto en `target`.

    Devuelve:
      - índice (posición) donde se debe cortar (después del separador).
    """
    if target >= len(text):
        return len(text)

    start = max(0, target - window)
    end = min(len(text), target + window)
    region = text[start:end]

    rel_target = target - start

    for sep in _SEPARATORS:
        pos = region.rfind(sep, 0, rel_target + len(sep))
        if pos != -1:
            return start + pos + len(sep)

    return target


def _merge_small_tail(chunks: list[str], *, min_tail_chars: int) -> list[str]:
    """
    Si el último chunk es demasiado chico, lo mergea con el anterior (si existe).

    Esto reduce fragmentación y mejora contexto para embeddings.
    """
    if len(chunks) < 2:
        return chunks

    last = chunks[-1]
    if len(last) >= min_tail_chars:
        return chunks

    merged = chunks[:-2] + [(chunks[-2].rstrip() + "\n\n" + last.lstrip()).strip()]
    return merged


def chunk_fragments(
    text: str,
    *,
    chunk_size: int = 900,
    overlap: int = 120,
    context_window: int = 80,
    max_chunks: int = _DEFAULT_MAX_CHUNKS,
) -> list[ChunkFragment]:
    """
    Parte el texto en fragmentos con overlap y metadata.

    Importante:
      - Este es el “motor” real. `chunk_text` es solo un wrapper.
    """
    raw = (text or "").strip()
    if not raw:
        return []

    if chunk_size <= 0:
        raise ValueError(f"chunk_size debe ser > 0. got={chunk_size}")
    if overlap < 0:
        raise ValueError(f"overlap debe ser >= 0. got={overlap}")
    if overlap >= chunk_size:
        raise ValueError("overlap debe ser menor a chunk_size.")
    if max_chunks <= 0:
        raise ValueError("max_chunks debe ser > 0.")

    # Caso corto: un fragmento único.
    if len(raw) <= chunk_size:
        return [
            ChunkFragment(
                content=raw,
                index=0,
                start=0,
                end=len(raw),
            )
        ]

    fragments: list[ChunkFragment] = []
    start = 0
    idx = 0

    while start < len(raw):
        if idx >= max_chunks:
            # Guardrail duro: mejor truncar que caer por memoria.
            # (Si querés, acá se puede levantar excepción tipada.)
            break

        end_target = start + chunk_size
        if end_target >= len(raw):
            piece = raw[start:].strip()
            if piece:
                fragments.append(
                    ChunkFragment(content=piece, index=idx, start=start, end=len(raw))
                )
            break

        split_at = _find_best_split(raw, end_target)
        piece = raw[start:split_at].strip()

        if piece:
            fragments.append(
                ChunkFragment(content=piece, index=idx, start=start, end=split_at)
            )
            idx += 1

        # Avanza con overlap, evitando loops por split muy chico.
        start = max(start + 1, split_at - overlap)

    # Enriquecer vecindad (prev/next context) para quien lo necesite.
    for i, frag in enumerate(fragments):
        prev_ctx = ""
        next_ctx = ""

        if i > 0:
            prev_ctx = fragments[i - 1].content[-context_window:]

        if i + 1 < len(fragments):
            next_ctx = fragments[i + 1].content[:context_window]

        fragments[i] = ChunkFragment(
            content=frag.content,
            index=frag.index,
            start=frag.start,
            end=frag.end,
            prev_context=prev_ctx,
            next_context=next_ctx,
            section=frag.section,
            kind=frag.kind,
        )

    return fragments


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    """
    Wrapper de compatibilidad: devuelve list[str].

    Mantiene contrato actual, pero internamente usa fragmentos ricos.
    """
    fragments = chunk_fragments(text, chunk_size=chunk_size, overlap=overlap)
    chunks = [f.content for f in fragments]

    # Mejora: si el último chunk es muy chico, mergearlo.
    # Heurística: “muy chico” = menos del 25% de chunk_size
    chunks = _merge_small_tail(chunks, min_tail_chars=max(80, int(chunk_size * 0.25)))

    return chunks


class SimpleTextChunker:
    """
    Servicio de chunking simple (baseline).

    Diseño:
      - Valida parámetros al construir.
      - `chunk()` delega a `chunk_text`.
    """

    def __init__(self, chunk_size: int = 900, overlap: int = 120):
        if chunk_size <= 0:
            raise ValueError(f"chunk_size debe ser > 0, got {chunk_size}")
        if overlap < 0:
            raise ValueError(f"overlap debe ser >= 0, got {overlap}")
        if overlap >= chunk_size:
            raise ValueError("overlap debe ser menor a chunk_size")

        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        return chunk_text(text, chunk_size=self.chunk_size, overlap=self.overlap)
