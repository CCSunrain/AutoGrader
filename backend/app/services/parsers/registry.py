"""Parser registry: dispatch by content type."""
from app.services.parsers.base import ParseResult, Parser
from app.services.parsers.markdown_parser import MarkdownParser
from app.services.parsers.pdf_parser import PdfParser

_PARSERS: dict[str, Parser] = {
    "pdf": PdfParser(),
    "markdown": MarkdownParser(),
    "md": MarkdownParser(),
}


def get_parser(content_type: str) -> Parser:
    key = (content_type or "").lower()
    if key not in _PARSERS:
        raise ValueError(f"unsupported content type: {content_type}")
    return _PARSERS[key]


def parse_document(data: bytes, content_type: str, filename: str = "") -> ParseResult:
    return get_parser(content_type).parse(data, filename)
