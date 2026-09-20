"""Grading engine: per-criterion evidence review.

For each rubric item it (1) asks the LLM to judge evidence state + suggested
band, (2) validates the band against the rubric scale, (3) locates quoted
evidence in the source text, and (4) runs deterministic contradiction
detection. Items the machine cannot settle are marked `needs_review` and are
NEVER auto-scored as zero.
"""
import difflib

from sqlalchemy.orm import Session

from app.models import Evidence, Review, ReviewItem
from app.services.ai_client import get_llm
from app.services.grading.contradiction import RULES_VERSION, detect_contradictions
from app.services.grading.json_utils import extract_json
from app.services.grading.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt

MAX_REPORT_CHARS = 12000
VALID_STATES = {"supported", "missing", "uncertain"}


def locate_quote(raw_text: str, quote: str) -> tuple[int, int] | None:
    """Locate `quote` in `raw_text`, returning (start, end); fuzzy-match as fallback."""
    q = quote.strip()
    if not q:
        return None
    idx = raw_text.find(q)
    if idx >= 0:
        return idx, idx + len(q)
    sm = difflib.SequenceMatcher(None, raw_text, q)
    m = sm.find_longest_match(0, len(raw_text), 0, len(q))
    if m.size >= max(3, len(q) // 2):
        return m.a, m.a + m.size
    return None


def _find_page(blocks: list[dict], offset: int) -> int | None:
    for b in blocks:
        if b.get("page") is not None and b["offset_start"] <= offset < b["offset_end"]:
            return b["page"]
    return None


def run_review(db: Session, review: Review, rubric_version, parsed_document) -> None:
    llm = get_llm()
    if llm is None:
        raise RuntimeError("LLM 未配置，无法评阅")

    raw_text = parsed_document.raw_text or ""
    content = parsed_document.content or {}
    blocks: list[dict] = content.get("blocks", [])
    contradictions = detect_contradictions(blocks)

    items = sorted(rubric_version.items, key=lambda it: it.order_index)
    report_text = raw_text[:MAX_REPORT_CHARS]

    for idx, item in enumerate(items):
        bands = sorted(item.bands, key=lambda b: b.order_index)
        band_names = [b.level for b in bands]

        user_content = build_user_prompt(
            item.name,
            item.description,
            [{"level": b.level, "score": b.score, "description": b.description} for b in bands],
            report_text,
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
        result = llm.chat(messages=messages, temperature=0.0, max_tokens=2000)
        parsed = extract_json(result.content)

        # structured-output retry: reasoning models may emit non-JSON on first pass
        if parsed is None:
            messages.append(
                {
                    "role": "user",
                    "content": "你上一次没有输出合法 JSON。请重新输出，只输出一个合法 JSON 对象，不要任何其他文字。",
                }
            )
            result = llm.chat(messages=messages, temperature=0.0, max_tokens=2000)
            parsed = extract_json(result.content)
        needs_review = False
        flags: list[str] = []
        evidence_state = "uncertain"
        suggested_band_id: str | None = None
        confidence = 0.0
        explanation = ""
        quotes: list[str] = []

        if parsed is None:
            needs_review = True
            flags.append("llm_json_parse_failed")
            explanation = result.content[:300]
        else:
            evidence_state = parsed.get("evidence_state", "uncertain")
            if evidence_state not in VALID_STATES:
                flags.append("invalid_evidence_state")
                evidence_state = "uncertain"
            try:
                confidence = float(parsed.get("confidence") or 0.0)
            except (TypeError, ValueError):
                confidence = 0.0
            explanation = str(parsed.get("explanation") or "")
            raw_quotes = parsed.get("quotes") or []
            quotes = [q for q in raw_quotes if isinstance(q, str) and q.strip()]

            sb = parsed.get("suggested_band")
            if sb in band_names:
                suggested_band_id = next(b.id for b in bands if b.level == sb)
            else:
                flags.append("band_not_in_scale")
                needs_review = True

        if evidence_state == "uncertain":
            needs_review = True
            flags.append("evidence_uncertain")
        if evidence_state == "supported" and not quotes:
            needs_review = True
            flags.append("supported_without_quote")

        review_item = ReviewItem(
            workspace_id=review.workspace_id,
            review_id=review.id,
            rubric_item_id=item.id,
            order_index=idx,
            evidence_state=evidence_state,
            suggested_band_id=suggested_band_id,
            confidence=confidence,
            explanation=explanation,
            needs_review=needs_review,
            review_flags=flags,
        )
        db.add(review_item)
        db.flush()

        for q in quotes:
            loc = locate_quote(raw_text, q)
            if loc is None:
                continue
            db.add(
                Evidence(
                    workspace_id=review.workspace_id,
                    review_item_id=review_item.id,
                    quote=q,
                    start_offset=loc[0],
                    end_offset=loc[1],
                    page=_find_page(blocks, loc[0]),
                    ref_type="text",
                )
            )

    review.contradictions = contradictions
    review.status = "done"
    review.prompt_version = PROMPT_VERSION
    review.rules_version = RULES_VERSION
    review.model = llm.model
    db.flush()
