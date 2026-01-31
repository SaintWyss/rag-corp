"""
===============================================================================
MÓDULO: Infrastructure / Parsers
===============================================================================

CRC CARD (Package)
-------------------------------------------------------------------------------
Nombre:
    infrastructure.parsers

Responsabilidades:
    - Exponer el adaptador principal usado por DI (SimpleDocumentTextExtractor).
    - Exponer la lista única de MIME soportados (SUPPORTED_MIME_TYPES).
    - Mantener el "public API" del paquete estable.

Colaboradores:
    - document_text_extractor.SimpleDocumentTextExtractor
    - mime_types.SUPPORTED_MIME_TYPES
===============================================================================
"""

from .document_text_extractor import SimpleDocumentTextExtractor
from .mime_types import SUPPORTED_MIME_TYPES

__all__ = ["SimpleDocumentTextExtractor", "SUPPORTED_MIME_TYPES"]
