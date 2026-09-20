"""Parser unit tests (no DB dependency)."""
import io

import fitz

from app.services.parsers.registry import parse_document


def _make_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Sorting Algorithm Report")
    page.insert_text((72, 100), "Quick sort, time complexity O(n log n).")
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def test_pdf_parser():
    result = parse_document(_make_pdf(), "pdf", "report.pdf")
    assert result.content_type == "pdf"
    assert result.page_count == 1
    assert "Quick sort" in result.raw_text
    paras = [b for b in result.blocks if b.type == "paragraph"]
    assert len(paras) >= 1
    assert paras[0].page == 1


MARKDOWN_SAMPLE = """# 排序算法实验报告

## 算法实现

使用快速排序，时间复杂度 O(n log n)。

```python
def quicksort(arr):
    return sorted(arr)
```

| 数据规模 | 运行时间 |
| --- | --- |
| 1000 | 0.01s |
| 10000 | 0.12s |

- 稳定性：否
- 空间复杂度：O(log n)
"""


def test_markdown_parser():
    result = parse_document(MARKDOWN_SAMPLE.encode(), "markdown", "report.md")
    types = [b.type for b in result.blocks]
    for expected in ("heading", "code", "table", "list", "paragraph"):
        assert expected in types, f"missing block type: {expected}"

    heading = next(b for b in result.blocks if b.type == "heading")
    assert heading.text == "排序算法实验报告"
    assert heading.level == 1

    code = next(b for b in result.blocks if b.type == "code")
    assert "quicksort" in code.text

    table = next(b for b in result.blocks if b.type == "table")
    assert table.table is not None and len(table.table) == 3
    assert table.table[0] == ["数据规模", "运行时间"]
    assert table.table[1] == ["1000", "0.01s"]

    lst = next(b for b in result.blocks if b.type == "list")
    assert "稳定性" in lst.text

    para = next(b for b in result.blocks if b.type == "paragraph")
    assert "快速排序" in result.raw_text[para.offset_start : para.offset_end]


def test_markdown_position_integrity():
    """每个 block 的 offset 都能在原文中定位到对应文本片段。"""
    result = parse_document(MARKDOWN_SAMPLE.encode(), "markdown", "report.md")
    for b in result.blocks:
        if not b.text:
            continue
        snippet = result.raw_text[b.offset_start : b.offset_end]
        # block.text 可能因 strip/join 与原文略有差异，用首个非空词校验定位
        first_word = b.text.strip().split()[0]
        assert first_word in snippet, f"block {b.type} offset mismatch"
