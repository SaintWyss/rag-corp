"""
===============================================================================
ARCHIVO: contracts.py
===============================================================================

CRC CARD (Module)
-------------------------------------------------------------------------------
Nombre:
    Contratos del Sub-sistema de Parsers

Responsabilidades:
    - Definir el contrato de parser (BaseParser) mediante Protocol.
    - Definir el resultado rico (ExtractedText) con metadatos y warnings.
    - Definir opciones compartidas (ParserOptions) para comportamiento consistente.

Colaboradores:
    - parsers específicos (PdfParser, DocxParser, TextParser)
    - registry.ParserRegistry
    - adapter document_text_extractor.SimpleDocumentTextExtractor
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ParserOptions:
    """
    Opciones compartidas para todos los parsers.

    Diseño:
      - Evitamos **kwargs para mantener contrato explícito (calidad senior).
      - max_pages: protección para PDFs grandes.
      - max_chars: protección downstream (chunking/embeddings/DB).
      - allow_empty: permite decidir si "vacío" es error o no.
      - normalize_whitespace: estabiliza texto para chunking.
      - encoding: para text/plain.
    """

    max_pages: int | None = 100
    max_chars: int | None = 1_000_000
    allow_empty: bool = True
    normalize_whitespace: bool = True
    encoding: str = "utf-8"


@dataclass(frozen=True)
class ExtractedText:
    """
    Resultado rico de extracción.

    content:
      Texto final.
    metadata:
      Metadatos técnicos (source, páginas, etc.). No depende de dominio.
    warnings:
      Avisos no fatales (páginas que fallaron, truncados, etc.).
    page_count:
      Cantidad total (si se puede determinar).
    was_truncated:
      Indica truncado (por páginas o por caracteres).
    """

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    page_count: int | None = None
    was_truncated: bool = False

    @property
    def is_empty(self) -> bool:
        """True si el texto está vacío o sólo whitespace."""
        return not self.content.strip()


@runtime_checkable
class BaseParser(Protocol):
    """
    Interfaz que deben implementar los parsers específicos.

    Nota:
      - Usamos Protocol para favorecer test doubles/mocks sin herencia forzada.
      - LSP: cualquier parser concreto debe ser intercambiable por este contrato.
    """

    def parse(self, content: bytes, *, options: ParserOptions) -> ExtractedText:
        """
        Parsear bytes -> texto + metadatos.

        Errores esperables:
          - DocumentParsingError
          - ParsingLimitExceededError
          - EmptyDocumentError (si allow_empty=False)
        """
        ...
