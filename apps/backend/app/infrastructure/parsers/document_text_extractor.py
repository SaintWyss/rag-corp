"""
Name: Document Text Extraction Adapter

Responsibilities:
  - Extract text from PDF/DOCX binaries
  - Normalize parser behavior behind a simple interface
"""

from io import BytesIO

from docx import Document as DocxDocument
from pypdf import PdfReader

from ...domain.services import DocumentTextExtractor


PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _extract_pdf(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def _extract_docx(content: bytes) -> str:
    doc = DocxDocument(BytesIO(content))
    return "\n".join(p.text for p in doc.paragraphs).strip()


class SimpleDocumentTextExtractor(DocumentTextExtractor):
    """R: Extract text from PDF/DOCX content."""

    def extract_text(self, mime_type: str, content: bytes) -> str:
        if mime_type == PDF_MIME:
            return _extract_pdf(content)
        if mime_type == DOCX_MIME:
            return _extract_docx(content)
        raise ValueError(f"Unsupported MIME type: {mime_type}")
