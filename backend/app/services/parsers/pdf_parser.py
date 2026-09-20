"""PDF parser built on PyMuPDF: text blocks, tables, images, with positions."""
import pymupdf as fitz  # PyMuPDF

from app.services.parsers.base import Block, ParseResult, Parser


class PdfParser(Parser):
    parser_version = "pdf-pymupdf-1"

    def parse(self, data: bytes, filename: str = "") -> ParseResult:
        doc = fitz.open(stream=data, filetype="pdf")
        page_count = doc.page_count

        page_texts: list[str] = []
        blocks: list[Block] = []

        for page_index in range(page_count):
            page = doc[page_index]
            page_no = page_index + 1
            page_text = page.get_text("text")
            page_texts.append(page_text)

            # text / image blocks (from structured dict)
            for raw in page.get_text("dict").get("blocks", []):
                if raw["type"] == 0:  # text block
                    text = "".join(
                        span.get("text", "")
                        for line in raw.get("lines", [])
                        for span in line.get("spans", [])
                    )
                    if text.strip():
                        blocks.append(
                            Block(
                                type="paragraph",
                                text=text,
                                page=page_no,
                                bbox=list(raw.get("bbox", [])),
                            )
                        )
                elif raw["type"] == 1:  # image block
                    blocks.append(
                        Block(type="image", text="", page=page_no, bbox=list(raw.get("bbox", [])))
                    )

            # tables (best-effort; simple bordered/rule tables are detected)
            try:
                for table in page.find_tables():
                    cells = table.extract() or []
                    table_text = "\n".join("\t".join(c or "" for c in row) for row in cells)
                    blocks.append(
                        Block(
                            type="table",
                            text=table_text,
                            page=page_no,
                            table=cells,
                            bbox=list(table.bbox) if table.bbox else None,
                        )
                    )
            except Exception:  # noqa: BLE001 - table detection is optional
                pass

        raw_text = "\n\n".join(page_texts)
        page_offsets = self._page_offsets(page_texts)

        # fill char offsets by locating each block's text within its page
        for block in blocks:
            if block.page is None or not block.text:
                continue
            pos = page_texts[block.page - 1].find(block.text)
            if pos >= 0:
                block.offset_start = page_offsets[block.page - 1] + pos
                block.offset_end = block.offset_start + len(block.text)

        doc.close()
        return ParseResult(
            content_type="pdf",
            parser_version=self.parser_version,
            raw_text=raw_text,
            blocks=blocks,
            page_count=page_count,
            meta={"filename": filename},
        )

    @staticmethod
    def _page_offsets(page_texts: list[str]) -> list[int]:
        offsets: list[int] = []
        running = 0
        for text in page_texts:
            offsets.append(running)
            running += len(text) + 2  # separator "\n\n"
        return offsets
