"""Parser base types and interface.

The parse result is a normalized list of `Block`s carrying position info
(page / line / char offset / bbox) so the grading engine can later locate
evidence in the original document ("原文定位").
"""
from dataclasses import asdict, dataclass, field


@dataclass
class Block:
    type: str  # paragraph | heading | code | table | list | image
    text: str = ""
    page: int | None = None  # PDF page (1-based)
    line_start: int | None = None  # Markdown line (1-based)
    line_end: int | None = None
    offset_start: int = 0  # char offset in raw_text
    offset_end: int = 0
    level: int | None = None  # heading level
    table: list[list[str]] | None = None  # table cells (row-major)
    bbox: list[float] | None = None  # PDF [x0, y0, x1, y1]
    meta: dict = field(default_factory=dict)


@dataclass
class ParseResult:
    content_type: str  # pdf | markdown
    parser_version: str
    raw_text: str
    blocks: list[Block] = field(default_factory=list)
    page_count: int | None = None
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class Parser:
    parser_version: str = "base"

    def parse(self, data: bytes, filename: str = "") -> ParseResult:
        raise NotImplementedError
