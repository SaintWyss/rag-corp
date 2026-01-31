from unittest.mock import MagicMock

import pytest
from app.infrastructure.parsers.contracts import BaseParser
from app.infrastructure.parsers.docx_parser import DocxParser
from app.infrastructure.parsers.errors import UnsupportedMimeTypeError
from app.infrastructure.parsers.pdf_parser import PdfParser
from app.infrastructure.parsers.registry import ParserRegistry, TextParser


def test_registry_returns_correct_parser_instances():
    registry = ParserRegistry()

    assert isinstance(registry.get_parser("application/pdf"), PdfParser)
    assert isinstance(registry.get_parser("text/plain"), TextParser)
    assert isinstance(
        registry.get_parser(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        DocxParser,
    )


def test_registry_normalizes_mime_types():
    registry = ParserRegistry()

    # Uppercase
    assert isinstance(registry.get_parser("APPLICATION/PDF"), PdfParser)
    # Parameters
    assert isinstance(registry.get_parser("text/plain; charset=utf-8"), TextParser)


def test_registry_raises_on_unsupported_mime():
    registry = ParserRegistry()

    with pytest.raises(UnsupportedMimeTypeError) as exc:
        registry.get_parser("image/png")

    assert exc.value.mime_type == "image/png"


def test_registry_allows_registering_new_parsers():
    registry = ParserRegistry()

    # Mock a new parser factory
    mock_parser = MagicMock(spec=BaseParser)
    registry.register("application/custom", lambda: mock_parser)

    parser = registry.get_parser("application/custom")
    assert parser == mock_parser
