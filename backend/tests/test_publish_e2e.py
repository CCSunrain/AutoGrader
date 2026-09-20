"""End-to-end test: review -> human decision -> publish -> immutable -> student view.

Run:  PYTHONPATH= uv run --project backend python backend/tests/test_publish_e2e.py
"""
import os
import sys

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://autograder:autograder@localhost:10080/autograder"
)

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: F401, E402
from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import ParsedDocument, Review, ReviewItem  # noqa: E402
from app.worker.main import handle_parse_document, handle_run_review  # noqa: E402

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)
results: list[tuple[str, bool]] = []


def ok(label: str, cond: bool) -> bool:
    results.append((label, cond))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")
    return cond


# 1. register teacher, course, assignment, rubric
r = client.post(
    "/api/auth/register", json={"email": "teacher@x.com", "username": "教师", "password": "password123"}
)
ok("register teacher", r.status_code == 201)
token = r.json()["access_token"]
h = {"Authorization": f"Bearer {token}"}

r = client.post("/api/courses", json={"name": "数据结构", "code": "CS101", "term": "2026秋"}, headers=h)
course_id = r.json()["id"]
r = client.post("/api/assignments", json={"course_id": course_id, "title": "排序算法实验"}, headers=h)
assignment_id = r.json()["id"]

rubric = {
    "title": "排序实验评分量表",
    "items": [
        {"name": "算法实现正确性", "max_score": 40, "order_index": 0,
         "bands": [
             {"level": "优秀", "score": 40, "order_index": 0},
             {"level": "良好", "score": 30, "order_index": 1},
             {"level": "及格", "score": 20, "order_index": 2},
             {"level": "不及格", "score": 0, "order_index": 3},
         ]},
        {"name": "复杂度分析", "max_score": 30, "order_index": 1,
         "bands": [
             {"level": "优秀", "score": 30, "order_index": 0},
             {"level": "良好", "score": 20, "order_index": 1},
             {"level": "及格", "score": 10, "order_index": 2},
             {"level": "不及格", "score": 0, "order_index": 3},
         ]},
    ],
}
r = client.post("/api/rubrics", json=rubric, headers=h)
ok("create rubric", r.status_code == 201)
rubric_version_id = r.json()["versions"][0]["id"]

# band id map: item_name -> {level: band_id}
with SessionLocal() as s:
    band_map = {it.name: {b.level: b.id for b in it.bands} for it in s.query(models.RubricItem).all()}

# 2. upload + parse + review
REPORT = """# 排序算法实验报告

## 算法实现

本实验实现了快速排序算法，时间复杂度为 O(n log n)，空间复杂度为 O(log n)。

```python
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + [pivot] + quicksort(right)
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
    data={"student_id": "stu-1"},
    headers=h,
)
ok("upload report", r.status_code == 201)
submission_id = r.json()["id"]
version_id = r.json()["versions"][-1]["id"]

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

# 3. collect review item ids (ordered)
with SessionLocal() as s:
    review = s.get(Review, review_id)
    items = sorted(review.items, key=lambda x: x.order_index)
    item0_id, item1_id = items[0].id, items[1].id

# 4. decision for item0 only, then try publish -> should fail
r = client.post(
    f"/api/review-items/{item0_id}/decision",
    json={"final_band_id": band_map["算法实现正确性"]["优秀"], "feedback": "实现正确"},
    headers=h,
)
ok("submit decision item0", r.status_code == 200)

r = client.post(f"/api/reviews/{review_id}/publish", json={"feedback": "总评"}, headers=h)
ok("publish blocked (item1 unreviewed)", r.status_code == 400)

# 5. invalid band (item1's band on item0) -> 400
r = client.post(
    f"/api/review-items/{item0_id}/decision",
    json={"final_band_id": band_map["复杂度分析"]["良好"], "feedback": ""},
    headers=h,
)
ok("invalid band rejected", r.status_code == 400)

# 6. decision for item1 (良好=20), then publish -> score 60
r = client.post(
    f"/api/review-items/{item1_id}/decision",
    json={"final_band_id": band_map["复杂度分析"]["良好"], "feedback": "复杂度表述正确"},
    headers=h,
)
ok("submit decision item1", r.status_code == 200)

r = client.post(f"/api/reviews/{review_id}/publish", json={"feedback": "总体完成良好"}, headers=h)
ok("publish success", r.status_code == 200)
ok("score = 60", r.json()["publish"]["score"] == 60)
ok("review status=published", r.json()["status"] == "published")

# 7. published is immutable
r = client.post(
    f"/api/review-items/{item0_id}/decision",
    json={"final_band_id": band_map["算法实现正确性"]["及格"], "feedback": ""},
    headers=h,
)
ok("published immutable", r.status_code == 400)

# 8. student view (published result)
r = client.get(f"/api/submissions/{submission_id}/published", headers=h)
ok("get published", r.status_code == 200)
ok("published score=60", r.json()["score"] == 60)
ok("published has 2 items", len(r.json()["items"]) == 2)
ok("item band level", r.json()["items"][0]["final_band_level"] == "优秀")

failed = [l for l, p in results if not p]
print("===", "ALL PASS" if not failed else f"FAILED: {failed}", "===")
sys.exit(1 if failed else 0)
