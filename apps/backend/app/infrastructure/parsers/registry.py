"""
===============================================================================
ARCHIVO: registry.py
===============================================================================

CRC CARD (Class)
-------------------------------------------------------------------------------
Clase:
    ParserRegistry

Responsabilidades:
    - Mantener el mapeo MIME -> Strategy (parser).
    - Resolver parser por MIME (con normalización).
    - Permitir extensión sin modificar consumidores (OCP) vía register().

Colaboradores:
    - mime_types.normalize_mime_type / SUPPORTED_MIME_TYPES
    - errors.UnsupportedMimeTypeError
    - PdfParser / DocxParser / TextParser
===============================================================================
"""

from __future__ import annotations

from collections.abc import Callable

from .contracts import BaseParser, ExtractedText, ParserOptions
from .docx_parser import DocxParser
from .errors import UnsupportedMimeTypeError
from .mime_types import (
    DOCX_MIME,
    PDF_MIME,
    SUPPORTED_MIME_TYPES,
    TXT_MIME,
    normalize_mime_type,
)
from .pdf_parser import PdfParser


class TextParser(BaseParser):
    """
    Parser simple para text/plain.

    Nota:
      - Esto existe para mantener consistencia: todo pasa por Strategy.
      - El adapter central aplica normalización/truncado también.
    """

    def parse(self, content: bytes, *, options: ParserOptions) -> ExtractedText:
        try:
            text = content.decode(options.encoding)
        except UnicodeDecodeError:
            text = content.decode(options.encoding, errors="replace")

        return ExtractedText(content=text, metadata={"source": "text"})


ParserFactory = Callable[[], BaseParser]


class ParserRegistry:
    """Registry/Factory de parsers por MIME."""

    def __init__(self) -> None:
        # Usamos factories (callables) para:
        # - instanciación tardía
        # - tests más simples (inyectar factories)
        self._factories: dict[str, ParserFactory] = {
            PDF_MIME: PdfParser,
            DOCX_MIME: DocxParser,
            TXT_MIME: TextParser,
        }

    def supported_mime_types(self) -> frozenset[str]:
        """Devuelve el set de MIME soportados (fuente única de verdad)."""
        return SUPPORTED_MIME_TYPES

    def register(self, mime_type: str, factory: ParserFactory) -> None:
        """
        Registrar/override de un parser.

        OCP:
          - Agregar soporte a Markdown/HTML/etc. sin tocar consumidores.
        """
        self._factories[normalize_mime_type(mime_type)] = factory

    def get_parser(self, mime_type: str) -> BaseParser:
        """
        Retorna un parser instanciado para el MIME solicitado.

        Errores:
          - UnsupportedMimeTypeError si no existe mapping.
        """
        normalized = normalize_mime_type(mime_type)
        factory = self._factories.get(normalized)

        if not factory:
            raise UnsupportedMimeTypeError(
                normalized, supported=set(self._factories.keys())
            )

        return factory()
