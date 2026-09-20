"""Versioned grading prompts.

The prompt version is bound to every Review so that a given suggestion can be
replayed / audited against the exact prompt used.
"""

PROMPT_VERSION = "grading-v1"

SYSTEM_PROMPT = (
    "你是一名严谨的高校《数据结构与算法》课程实验报告助教，负责对报告逐项评阅。"
    "你只输出一个 JSON 对象，不要输出任何解释性文字、markdown 代码块标记或前后缀。"
)


def build_user_prompt(
    item_name: str,
    item_description: str,
    bands: list[dict],
    report_text: str,
) -> str:
    """bands: [{"level": str, "score": int, "description": str}, ...]"""
    band_lines = "\n".join(
        f"- {b['level']}={b['score']}: {b.get('description') or '（无说明）'}" for b in bands
    )
    return (
        f"评分项：{item_name}\n"
        f"评分项说明：{item_description or '（无）'}\n"
        f"允许的档位（档位名=分值）：\n{band_lines}\n\n"
        f"以下是学生实验报告的解析文本：\n"
        f"<<<报告开始>>>\n{report_text}\n<<<报告结束>>>\n\n"
        "请判断报告对该评分项的证据状态并给出建议档位，只输出如下 JSON：\n"
        '{"evidence_state": "supported|missing|uncertain", '
        '"suggested_band": "档位名", "confidence": 0.0, '
        '"explanation": "简短说明", "quotes": ["原文证据片段"]}\n\n'
        "规则：\n"
        "- evidence_state：supported=有明确原文证据支持；missing=报告缺失该项要求内容；"
        "uncertain=证据含糊或无法确定。\n"
        "- suggested_band 必须是上面列出的档位名之一；证据缺失时取最低档。\n"
        "- quotes 必须逐字引用原文（可多个），不得改写、缩写或概括，用于在原文中定位。\n"
        "- confidence 是 0.0~1.0 的置信度。\n"
        "- 只输出 JSON 本身。"
    )
