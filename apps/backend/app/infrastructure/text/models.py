"""
===============================================================================
CRC CARD — infrastructure/text/models.py
===============================================================================

Modelo:
  ChunkFragment (salida rica de chunking)

Responsabilidades:
  - Representar un chunk con metadata útil (índices/vecindad).
  - Permitir chunking más “analista” sin romper el contrato actual (list[str]).

Colaboradores:
  - infrastructure/text/chunker.py
  - infrastructure/text/structured_chunker.py
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkFragment:
    """
    Fragmento de texto con metadata útil.

    Notas:
      - start/end son offsets en caracteres sobre el texto original.
      - prev_context/next_context ayudan a “coser” continuidad si se desea.
    """

    content: str
    index: int
    start: int
    end: int
    prev_context: str = ""
    next_context: str = ""
    section: str | None = None
    kind: str = "text"  # text|header|code|list|table
