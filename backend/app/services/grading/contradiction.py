"""Deterministic contradiction detection over parsed tables.

Implements a concrete, explainable rule (not LLM-based): when a table has two
or more numeric columns and the first numeric column (the "scale") is strictly
increasing while another numeric column (e.g. running time) decreases, that is
flagged as a numeric contradiction — e.g. larger input size but shorter time.
"""
RULES_VERSION = "contradiction-v1"


def _is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def detect_contradictions(blocks: list[dict]) -> list[dict]:
    """Return a list of contradiction dicts found across table blocks.

    `blocks` are the JSON-decoded blocks from ParsedDocument.content (dicts).
    """
    contradictions: list[dict] = []
    for bi, block in enumerate(blocks):
        if block.get("type") != "table" or not block.get("table"):
            continue
        rows = block["table"]
        if len(rows) < 3:  # header + at least 2 data rows
            continue

        # skip header row: numeric detection only over data rows
        data_rows = rows[1:]
        matrix: list[list[float | None]] = [
            [float(c) if _is_number(c) else None for c in row] for row in data_rows
        ]
        ncols = max(len(r) for r in matrix) if matrix else 0
        # numeric columns: every data row's cell is numeric
        numeric_cols = [
            c for c in range(ncols) if all(r[c] is not None for r in matrix if c < len(r))
        ]
        if len(numeric_cols) < 2:
            continue

        base = numeric_cols[0]
        base_vals = [r[base] for r in matrix]
        # only apply when the base column is strictly increasing
        if not all(base_vals[i] < base_vals[i + 1] for i in range(len(base_vals) - 1)):
            continue

        for col in numeric_cols[1:]:
            vals = [r[col] for r in matrix]
            for i in range(len(vals) - 1):
                if vals[i] > vals[i + 1]:
                    contradictions.append(
                        {
                            "table_index": bi,
                            "scale_col": base,
                            "value_col": col,
                            "row": i + 1,
                            "before": vals[i],
                            "after": vals[i + 1],
                            "message": (
                                f"第{bi + 1}个表格：基准列（第{base + 1}列）递增时，"
                                f"第{col + 1}列出现 {vals[i]} > {vals[i + 1]} 的反向下降，"
                                "可能存在数值矛盾"
                            ),
                        }
                    )
                    break  # report once per column

    return contradictions
