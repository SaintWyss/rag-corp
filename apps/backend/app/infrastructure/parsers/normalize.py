"""
===============================================================================
ARCHIVO: normalize.py
===============================================================================

CRC CARD (Module)
-------------------------------------------------------------------------------
Nombre:
    Normalización y Truncado de Texto

Responsabilidades:
    - Normalizar texto extraído de forma consistente (evitar basura/ruido).
    - Aplicar truncado por caracteres (sostenibilidad: evita explosiones downstream).

Colaboradores:
    - pdf_parser.PdfParser
    - docx_parser.DocxParser
    - document_text_extractor.SimpleDocumentTextExtractor
===============================================================================
"""

from __future__ import annotations

import re

_NULL_CHAR = "\x00"


def normalize_text(text: str, *, collapse_whitespace: bool) -> str:
    """
    Normaliza texto para consumo estable.

    Qué hace:
      - Elimina caracteres NULL.
      - strip() para quitar extremos.
      - Opcionalmente colapsa whitespace excesivo para chunking más estable.

    Por qué:
      - PDFs y DOCX a veces generan secuencias raras o saltos de línea gigantes.
      - Normalizar ayuda a consistencia de embeddings y chunking.
    """
    if not text:
        return ""

    text = text.replace(_NULL_CHAR, "").strip()

    if collapse_whitespace:
        # Espacios y tabs repetidos -> un solo espacio
        text = re.sub(r"[ \t]+", " ", text)
        # Más de 2 saltos de línea -> 2 (mantiene separación de párrafos)
        text = re.sub(r"\n{3,}", "\n\n", text)

    return text


def truncate_text(text: str, *, max_chars: int | None) -> tuple[str, bool]:
    """
    Trunca texto según max_chars y devuelve (texto, was_truncated).

    Nota:
      - max_chars=None o <=0 => no trunca.
      - Esto protege pipeline (chunking/embeddings/DB).
    """
    if max_chars is None or max_chars <= 0:
        return text, False
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars], True
