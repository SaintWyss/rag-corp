"""
===============================================================================
ARCHIVO: errors.py
===============================================================================

CRC CARD (Module)
-------------------------------------------------------------------------------
Nombre:
    Excepciones Tipadas del Sub-sistema de Parsers

Responsabilidades:
    - Modelar errores explícitos (sin ValueError genérico).
    - Transportar contexto útil (original_error, límites, MIME, etc.).
    - Permitir mapping consistente a "FAILED" / respuestas HTTP / métricas.

Colaboradores:
    - pdf_parser.PdfParser
    - docx_parser.DocxParser
    - registry.ParserRegistry
    - capa que persiste/propaga errores (worker/use case)
===============================================================================
"""

from __future__ import annotations


class ParserError(Exception):
    """
    Error base de todo el sub-sistema de parsing.

    Nota:
      - Mantener jerarquía clara permite handling consistente.
      - "code" ayuda a registrar métricas/observabilidad.
    """

    code: str = "PARSER_ERROR"


class UnsupportedMimeTypeError(ParserError):
    """Se lanza cuando no existe parser registrado para el MIME."""

    code = "UNSUPPORTED_MIME_TYPE"

    def __init__(self, mime_type: str, *, supported: set[str] | None = None) -> None:
        supported_msg = f" Soportados: {sorted(supported)}" if supported else ""
        super().__init__(f"No hay parser para MIME: {mime_type}.{supported_msg}")
        self.mime_type = mime_type
        self.supported = supported or set()


class DocumentParsingError(ParserError):
    """Se lanza cuando el documento está corrupto/malformado o el parser falla."""

    code = "PARSING_FAILED"

    def __init__(
        self, message: str, *, original_error: Exception | None = None
    ) -> None:
        super().__init__(message)
        self.original_error = original_error


class ParsingLimitExceededError(ParserError):
    """Se lanza cuando el documento supera límites duros (protección anti-bombas)."""

    code = "LIMIT_EXCEEDED"

    def __init__(self, *, limit_name: str, actual: int, maximum: int) -> None:
        super().__init__(f"Límite excedido: {limit_name} ({actual} > {maximum})")
        self.limit_name = limit_name
        self.actual = actual
        self.maximum = maximum


class EmptyDocumentError(ParserError):
    """
    Se lanza cuando el texto extraído queda vacío.

    Ejemplo típico:
      - PDF escaneado sin OCR -> extract_text() retorna vacío.
    """

    code = "EMPTY_DOCUMENT"

    def __init__(self, message: str = "El texto extraído está vacío") -> None:
        super().__init__(message)
