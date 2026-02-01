"""
===============================================================================
CRC CARD — infrastructure/text/structured_chunker.py
===============================================================================

Clase:
  StructuredTextChunker (Strategy)

Responsabilidades:
  - Preservar estructura básica de documentos técnicos:
      * headers markdown
      * code blocks (```...```)
      * listas
  - Evitar cortes “en el medio” de bloques de código.
  - Devolver list[str] para compatibilidad con el contrato actual.

Colaboradores:
  - infrastructure/text/models.py (ChunkFragment, opcional)

Nota:
  - Este chunker apunta a mejorar calidad RAG en documentos técnicos.
===============================================================================
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

# Detectores (simples y determinísticos)
_CODE_BLOCK: Final[re.Pattern] = re.compile(r"```[\s\S]*?```", re.MULTILINE)
_MD_HEADER: Final[re.Pattern] = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_PARAGRAPH_BREAK: Final[re.Pattern] = re.compile(r"\n\s*\n")


@dataclass(frozen=True)
class _Section:
    title: str | None
    content: str


class StructuredTextChunker:
    """
    Chunker estructural.

    Parámetros:
      - max_chunk_size: tamaño máximo por chunk (caracteres)
      - overlap: overlap entre chunks (caracteres) aplicado al “pack final”
    """

    def __init__(self, max_chunk_size: int = 900, overlap: int = 120) -> None:
        if max_chunk_size <= 0:
            raise ValueError("max_chunk_size debe ser > 0.")
        if overlap < 0:
            raise ValueError("overlap debe ser >= 0.")
        if overlap >= max_chunk_size:
            raise ValueError("overlap debe ser menor a max_chunk_size.")

        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        raw = (text or "").strip()
        if not raw:
            return []

        # 1) Proteger bloques de código (no se parten).
        code_blocks: list[str] = []

        def _save_code(m: re.Match) -> str:
            code_blocks.append(m.group(0))
            return f"\x00CODE_{len(code_blocks) - 1}\x00"

        protected = _CODE_BLOCK.sub(_save_code, raw)

        # 2) Separar por headers markdown (si existen).
        sections = self._split_by_headers(protected)

        # 3) Empaquetar párrafos por sección hasta max_chunk_size.
        packed: list[str] = []
        for s in sections:
            packed.extend(self._pack_section(s))

        # 4) Restaurar bloques de código.
        restored: list[str] = []
        for c in packed:
            for i, block in enumerate(code_blocks):
                c = c.replace(f"\x00CODE_{i}\x00", block)
            restored.append(c.strip())

        # 5) Aplicar overlap final (opcional) para no perder continuidad.
        return self._apply_overlap(restored)

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------

    def _split_by_headers(self, text: str) -> list[_Section]:
        """
        Convierte el texto en secciones:
          - (header + contenido) por cada encabezado
          - si no hay headers, retorna una sección única
        """
        matches = list(_MD_HEADER.finditer(text))
        if not matches:
            return [_Section(title=None, content=text)]

        sections: list[_Section] = []
        last_end = 0
        current_title: str | None = None

        for m in matches:
            start = m.start()
            header_line = m.group(0).strip()
            title = m.group(2).strip()

            # contenido anterior al header actual
            if start > last_end:
                prev = text[last_end:start].strip()
                if prev:
                    sections.append(_Section(title=current_title, content=prev))

            current_title = title
            last_end = m.end()

            # guardamos el header “como parte” del contenido (para grounding)
            sections.append(_Section(title=current_title, content=header_line))

        # remanente
        tail = text[last_end:].strip()
        if tail:
            sections.append(_Section(title=current_title, content=tail))

        # Merge simple: header chunk + contenido inmediato si hay.
        merged: list[_Section] = []
        i = 0
        while i < len(sections):
            if i + 1 < len(sections) and sections[i].content.startswith("#"):
                # merge header + siguiente sección
                merged.append(
                    _Section(
                        title=sections[i].title,
                        content=(
                            sections[i].content + "\n\n" + sections[i + 1].content
                        ).strip(),
                    )
                )
                i += 2
            else:
                merged.append(sections[i])
                i += 1

        return merged

    def _pack_section(self, section: _Section) -> list[str]:
        """
        Empaqueta párrafos en chunks <= max_chunk_size.
        """
        paragraphs = [
            p.strip() for p in _PARAGRAPH_BREAK.split(section.content) if p.strip()
        ]
        chunks: list[str] = []

        current = ""
        for p in paragraphs:
            candidate = (current + "\n\n" + p).strip() if current else p
            if len(candidate) > self.max_chunk_size and current:
                chunks.append(current.strip())
                current = p
            else:
                current = candidate

        if current.strip():
            chunks.append(current.strip())

        return chunks

    def _apply_overlap(self, chunks: list[str]) -> list[str]:
        """
        Aplica overlap simple entre chunks contiguos.

        Motivo:
          - Evitar pérdida de contexto en cortes.
        """
        if not chunks or self.overlap <= 0:
            return chunks

        out: list[str] = []
        for i, c in enumerate(chunks):
            if i == 0:
                out.append(c)
                continue

            prev = out[-1]
            tail = prev[-self.overlap :]
            out.append((tail + "\n\n" + c).strip())

        return out
