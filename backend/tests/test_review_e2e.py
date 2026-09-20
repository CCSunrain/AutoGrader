"""End-to-end test for evidence review (real PG + real MiMo model).

Run:  PYTHONPATH= uv run --project backend python backend/tests/test_review_e2e.py
"""
import os
import sys
import uuid

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://autograder:autograder@localhost:10080/autograder"
)

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: F401, E402
from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import ParsedDocument, Review  # noqa: E402
from app.worker.main import handle_parse_document, handle_run_review  # noqa: E402

# 重建表（Review 模型新增了 contradictions 字段）
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)
results: list[tuple[str, bool]] = []


def ok(label: str, cond: bool) -> bool:
    results.append((label, cond))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")
    return cond


suffix = uuid.uuid4().hex[:8]

# 1. register teacher, course, assignment, rubric
r = client.post(
    "/api/auth/register",
    json={"email": f"t-{suffix}@x.com", "username": "教师", "password": "password123"},
)
ok("register teacher", r.status_code == 201)
token = r.json()["access_token"]
h = {"Authorization": f"Bearer {token}"}

r = client.post("/api/courses", json={"name": "数据结构", "code": f"CS{suffix}", "term": "2026秋"}, headers=h)
course_id = r.json()["id"]

r = client.post(
    "/api/assignments", json={"course_id": course_id, "title": "排序算法实验"}, headers=h
)
assignment_id = r.json()["id"]

rubric = {
    "title": "排序实验评分量表",
    "items": [
        {
            "name": "算法实现正确性",
            "max_score": 40,
            "order_index": 0,
            "bands": [
                {"level": "优秀", "score": 40, "order_index": 0},
                {"level": "良好", "score": 30, "order_index": 1},
                {"level": "及格", "score": 20, "order_index": 2},
                {"level": "不及格", "score": 0, "order_index": 3},
            ],
        },
        {
            "name": "复杂度分析",
            "max_score": 30,
            "order_index": 1,
            "bands": [
                {"level": "优秀", "score": 30, "order_index": 0},
                {"level": "良好", "score": 20, "order_index": 1},
                {"level": "及格", "score": 10, "order_index": 2},
                {"level": "不及格", "score": 0, "order_index": 3},
            ],
        },
    ],
}
r = client.post("/api/rubrics", json=rubric, headers=h)
ok("create rubric", r.status_code == 201)
rubric_version_id = r.json()["versions"][0]["id"]

# 收集合法档位 id 用于后续校验
band_ids = set()
with SessionLocal() as s:
    for item in s.query(models.RubricItem).all():
        for band in item.bands:
            band_ids.add(band.id)

# 2. upload a markdown report with a numeric contradiction in the table
REPORT = """# 排序算法实验报告

## 算法实现

本实验实现了快速排序算法，时间复杂度为 O(n log n)，空间复杂度为 O(log n)。

```python
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
```

## 实验结果

| 数据规模 | 运行时间(ms) |
| --- | --- |
| 1000 | 1.5 |
| 10000 | 0.8 |
| 100000 | 12.4 |
"""
r = client.post(
    f"/api/assignments/{assignment_id}/submissions",
    files={"file": ("report.md", REPORT.encode(), "text/markdown")},
    data={"student_id": f"stu-{suffix}"},
    headers=h,
)
ok("upload report", r.status_code == 201)
version_id = r.json()["versions"][-1]["id"]

# 3. parse + review
with SessionLocal() as s:
    parsed = s.query(ParsedDocument).filter_by(submission_version_id=version_id).first()
    parsed_id = parsed.id
handle_parse_document({"submission_version_id": version_id, "parsed_document_id": parsed_id})

r = client.post(
    f"/api/submission-versions/{version_id}/reviews",
    json={"rubric_version_id": rubric_version_id},
    headers=h,
)
ok("create review", r.status_code == 201)
review_id = r.json()["id"]

handle_run_review({"review_id": review_id})

# 4. verify review result
with SessionLocal() as s:
    review = s.get(Review, review_id)
    ok("review status=done", review.status == "done")
    ok("review has 2 items", len(review.items) == 2)
    ok("model bound", bool(review.model))
    ok("prompt version bound", review.prompt_version == "grading-v1")
    ok("rules version bound", review.rules_version == "contradiction-v1")

    ok("contradiction detected", len(review.contradictions) >= 1)

    for item in review.items:
        ok(f"item {item.order_index} state valid", item.evidence_state in ("supported", "missing", "uncertain"))
        if item.suggested_band_id is not None:
            ok(f"item {item.order_index} band in scale", item.suggested_band_id in band_ids)
        elif item.needs_review:
            ok(f"item {item.order_index} band empty -> needs_review", True)

    # 证据定位：至少一条 evidence 有有效 offset
    any_evidence = any(len(it.evidences) > 0 for it in review.items)
    ok("evidence located", any_evidence)
    if any_evidence:
        ev = next(it.evidences[0] for it in review.items if it.evidences)
        ok("evidence offset valid", 0 <= ev.start_offset < ev.end_offset)
        ok("evidence quote matches", REPORT[ev.start_offset : ev.end_offset].strip() == ev.quote.strip())

failed = [l for l, p in results if not p]
print("===", "ALL PASS" if not failed else f"FAILED: {failed}", "===")
sys.exit(1 if failed else 0)
