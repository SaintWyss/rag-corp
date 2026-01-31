"""
===============================================================================
ARCHIVO: pdf_parser.py
===============================================================================

CRC CARD (Class)
-------------------------------------------------------------------------------
Clase:
    PdfParser

Responsabilidades:
    - Extraer texto desde PDF usando pypdf.
    - Aplicar límites defensivos (páginas + chars vía adapter/normalizer).
    - Ser tolerante a fallos parciales (una página rota no tumba todo).
    - Emitir warnings útiles (observabilidad).

Colaboradores:
    - contracts.ParserOptions / ExtractedText
    - errors.DocumentParsingError / EmptyDocumentError
    - normalize.normalize_text / truncate_text
===============================================================================
"""

from __future__ import annotations

from io import BytesIO

from .contracts import BaseParser, ExtractedText, ParserOptions
from .errors import DocumentParsingError, EmptyDocumentError
from .normalize import normalize_text, truncate_text


class PdfParser(BaseParser):
    """Estrategia de parsing para PDFs (pypdf)."""

    def parse(self, content: bytes, *, options: ParserOptions) -> ExtractedText:
        # Lazy import: mejora cold start del worker/api
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise DocumentParsingError(
                "La librería 'pypdf' no está instalada", original_error=e
            ) from e

        # Abrir PDF (strict=False reduce fallos por PDFs imperfectos)
        try:
            reader = PdfReader(BytesIO(content), strict=False)
        except Exception as e:
            raise DocumentParsingError(
                "No se pudo abrir el PDF (archivo corrupto o inválido)",
                original_error=e,
            ) from e

        warnings: list[str] = []

        # page_count es best-effort: PDFs raros pueden fallar
        page_count: int | None
        try:
            page_count = len(reader.pages)
        except Exception:
            page_count = None
            warnings.append(
                "No se pudo determinar la cantidad total de páginas del PDF"
            )

        max_pages = (
            options.max_pages if (options.max_pages and options.max_pages > 0) else None
        )

        extracted_parts: list[str] = []
        truncated_by_pages = False

        # Iteración defensiva por página:
        # - si una página rompe, agregamos warning y seguimos
        for i, page in enumerate(reader.pages):
            if max_pages is not None and i >= max_pages:
                truncated_by_pages = True
                warnings.append(f"PDF truncado por max_pages={max_pages}")
                break

            try:
                text = page.extract_text() or ""
            except Exception as e:
                warnings.append(
                    f"Fallo al extraer texto de página {i}: {type(e).__name__}"
                )
                continue

            if text.strip():
                extracted_parts.append(text)

        raw_text = "\n".join(extracted_parts)

        # Normalización y truncado por chars (sostenibilidad)
        normalized = normalize_text(
            raw_text, collapse_whitespace=options.normalize_whitespace
        )
        normalized, truncated_by_chars = truncate_text(
            normalized, max_chars=options.max_chars
        )

        result = ExtractedText(
            content=normalized,
            metadata={"source": "pdf"},
            warnings=warnings,
            page_count=page_count,
            was_truncated=truncated_by_pages or truncated_by_chars,
        )

        # Política de vacío
        if result.is_empty and not options.allow_empty:
            raise EmptyDocumentError(
                "PDF sin texto extraíble (posible escaneo sin OCR)"
            )

        return result
