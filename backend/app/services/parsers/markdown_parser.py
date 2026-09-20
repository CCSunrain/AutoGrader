"""Markdown parser (lightweight, position-aware).

Extracts heading / code fence / GFM pipe-table / list / paragraph blocks with
1-based line ranges and char offsets, so evidence can be located in the source.
"""
import re

from app.services.parsers.base import Block, ParseResult, Parser

_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_LIST_ITEM = re.compile(r"^\s*([-*+]|\d+[.)])\s+(.*)$")
_TABLE_SEP = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")


class MarkdownParser(Parser):
    parser_version = "markdown-simple-1"

    def parse(self, data: bytes, filename: str = "") -> ParseResult:
        text = data.decode("utf-8", errors="replace")
        lines = text.split("\n")
        n = len(lines)

        # per-line start offsets (accounting for the trailing newline)
        line_offsets: list[int] = []
        running = 0
        for ln in lines:
            line_offsets.append(running)
            running += len(ln) + 1

        blocks: list[Block] = []
        i = 0
        while i < n:
            line = lines[i]

            if not line.strip():
                i += 1
                continue

            # code fence
            m = _FENCE.match(line)
            if m:
                fence = m.group(1)[:3]
                lang = line[m.end():].strip()
                start_line = i + 1
                buf: list[str] = []
                i += 1
                while i < n and not lines[i].strip().startswith(fence):
                    buf.append(lines[i])
                    i += 1
                if i < n:
                    i += 1  # skip closing fence
                blocks.append(
                    Block(
                        type="code",
                        text="\n".join(buf),
                        line_start=start_line,
                        line_end=i,
                        meta={"lang": lang},
                    )
                )
                continue

            # GFM pipe table
            if "|" in line and i + 1 < n and "-" in lines[i + 1] and _TABLE_SEP.match(lines[i + 1]):
                table, end_i = self._parse_table(lines, i)
                cells_text = "\n".join("\t".join(c or "" for c in row) for row in table)
                blocks.append(
                    Block(
                        type="table",
                        text=cells_text,
                        table=table,
                        line_start=i + 1,
                        line_end=end_i,
                    )
                )
                i = end_i
                continue

            # heading
            m = _HEADING.match(line)
            if m:
                blocks.append(
                    Block(
                        type="heading",
                        text=m.group(2).strip(),
                        level=len(m.group(1)),
                        line_start=i + 1,
                        line_end=i + 1,
                    )
                )
                i += 1
                continue

            # list
            if _LIST_ITEM.match(line):
                start_line = i + 1
                items: list[str] = []
                while i < n:
                    mm = _LIST_ITEM.match(lines[i])
                    if not mm:
                        break
                    items.append(mm.group(2).strip())
                    i += 1
                blocks.append(
                    Block(type="list", text="\n".join(items), line_start=start_line, line_end=i)
                )
                continue

            # paragraph: merge consecutive plain lines
            start_line = i + 1
            buf = [line.strip()]
            i += 1
            while i < n and lines[i].strip() and not self._is_block_start(lines[i]):
                buf.append(lines[i].strip())
                i += 1
            blocks.append(
                Block(type="paragraph", text=" ".join(buf), line_start=start_line, line_end=i)
            )

        # fill char offsets from line ranges
        for b in blocks:
            if b.line_start is None or b.line_end is None:
                continue
            b.offset_start = line_offsets[b.line_start - 1]
            last_idx = b.line_end - 1
            if 0 <= last_idx < n:
                b.offset_end = line_offsets[last_idx] + len(lines[last_idx])
            else:
                b.offset_end = b.offset_start + len(b.text)

        return ParseResult(
            content_type="markdown",
            parser_version=self.parser_version,
            raw_text=text,
            blocks=blocks,
            meta={"filename": filename},
        )

    def _parse_table(self, lines: list[str], i: int) -> tuple[list[list[str]], int]:
        n = len(lines)
        rows = [self._split_row(lines[i])]
        i += 2  # skip header + separator row
        while i < n and lines[i].strip() and "|" in lines[i]:
            rows.append(self._split_row(lines[i]))
            i += 1
        return rows, i

    @staticmethod
    def _split_row(line: str) -> list[str]:
        line = line.strip()
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|"):
            line = line[:-1]
        return [c.strip() for c in line.split("|")]

    @staticmethod
    def _is_block_start(line: str) -> bool:
        s = line.strip()
        if not s:
            return True
        if _FENCE.match(line) or _HEADING.match(s) or _LIST_ITEM.match(line):
            return True
        if "|" in s and "-" in s and _TABLE_SEP.match(s):
            return True
        return False
