"""
===============================================================================
ARCHIVO: document_text_extractor.py
===============================================================================

CRC CARD (Class)
-------------------------------------------------------------------------------
Clase:
    SimpleDocumentTextExtractor (Adapter)

Responsabilidades:
    - Adaptar el sub-sistema de parsers al contrato del dominio (DocumentTextExtractor).
    - Elegir Strategy correcta mediante ParserRegistry.
    - Aplicar opciones globales (ParserOptions) de forma consistente.
    - Retornar solo str (compatibilidad), descartando metadata por ahora.

Colaboradores:
    - domain.services.DocumentTextExtractor (contrato)
    - registry.ParserRegistry
    - contracts.ParserOptions
    - normalize.normalize_text / truncate_text
===============================================================================
"""

from __future__ import annotations

from ...domain.services import DocumentTextExtractor
from .contracts import ParserOptions
from .normalize import normalize_text, truncate_text
from .registry import ParserRegistry


class SimpleDocumentTextExtractor(DocumentTextExtractor):
    """
    Implementación concreta del servicio del dominio, respaldada por ParserRegistry.

    SOLID:
      - DIP: recibe registry/opciones por constructor (testeable y desacoplado).
      - SRP: solo coordina. No conoce detalles PDF/DOCX.
    """

    def __init__(
        self,
        registry: ParserRegistry | None = None,
        options: ParserOptions | None = None,
    ) -> None:
        self._registry = registry or ParserRegistry()
        self._options = options or ParserOptions()

    def extract_text(self, mime_type: str, content: bytes) -> str:
        """
        Extrae texto desde bytes usando la Strategy adecuada.

        Nota:
          - El dominio hoy espera 'str'. Internamente usamos ExtractedText
            para poder crecer (warnings, truncado, metadatos).
        """
        parser = self._registry.get_parser(mime_type)
        extracted = parser.parse(content, options=self._options)

        # Capa final de higiene: asegura consistencia aunque un parser se “olvide”
        text = normalize_text(
            extracted.content, collapse_whitespace=self._options.normalize_whitespace
        )
        text, _ = truncate_text(text, max_chars=self._options.max_chars)

        return text
