"""验证评阅 engine：两次采样（模型冲突）+ 矛盾关联评分项。

使用独立测试库 autograder_test，宿主机内手动调用 handler（读写本地 uploads 一致），
与 docker 的 worker/volume 完全隔离。
"""
import os
import sys

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://autograder:autograder@localhost:10080/autograder_test"
)

from fastapi.testclient import TestClient  # noqa: E402

from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import ParsedDocument, Review  # noqa: E402
from app.worker.main import handle_parse_document, handle_run_review  # noqa: E402

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)
results: list[tuple[str, bool]] = []


def ok(label, cond):
    results.append((label, cond))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}", flush=True)


r = client.post("/api/auth/register", json={"email": "t@x.com", "username": "老师", "password": "password123", "account_type": "teacher"})
h = {"Authorization": f"Bearer {r.json()['access_token']}"}
r = client.post("/api/courses", json={"name": "数据结构", "code": "CS101"}, headers=h)
course_id = r.json()["id"]
r = client.post("/api/assignments", json={"course_id": course_id, "title": "排序实验"}, headers=h)
assignment_id = r.json()["id"]

rubric = {
    "title": "排序量表",
    "items": [
        {"name": "算法实现正确性", "max_score": 40, "order_index": 0,
         "bands": [{"level": "优秀", "score": 40, "order_index": 0}, {"level": "良好", "score": 30, "order_index": 1}, {"level": "及格", "score": 20, "order_index": 2}, {"level": "不及格", "score": 0, "order_index": 3}]},
        {"name": "实验数据与结论", "max_score": 30, "order_index": 1,
         "bands": [{"level": "优秀", "score": 30, "order_index": 0}, {"level": "良好", "score": 20, "order_index": 1}, {"level": "及格", "score": 10, "order_index": 2}, {"level": "不及格", "score": 0, "order_index": 3}]},
    ],
}
r = client.post("/api/rubrics", json=rubric, headers=h)
rubric_version_id = r.json()["versions"][0]["id"]

REPORT = """# 排序算法实验报告

## 算法实现

本实验实现了快速排序，采用分治策略，平均时间复杂度 O(n log n)。

## 复杂度分析

平均 O(n log n)，最坏 O(n²)，空间 O(log n)。

## 实验数据

| 数据规模 | 运行时间(ms) |
| --- | --- |
| 1000 | 50.0 |
| 10000 | 10.0 |
"""
r = client.post(
    f"/api/assignments/{assignment_id}/submissions",
    files={"file": ("r.md", REPORT.encode(), "text/markdown")},
    data={"student_id": "stu-1"},
    headers=h,
)
version_id = r.json()["versions"][-1]["id"]

with SessionLocal() as s:
    parsed = s.query(ParsedDocument).filter_by(submission_version_id=version_id).first()
    parsed_id = parsed.id
handle_parse_document({"submission_version_id": version_id, "parsed_document_id": parsed_id})

r = client.post(f"/api/submission-versions/{version_id}/reviews", json={"rubric_version_id": rubric_version_id}, headers=h)
review_id = r.json()["id"]
handle_run_review({"review_id": review_id})

with SessionLocal() as s:
    review = s.get(Review, review_id)
    ok("review done", review.status == "done")
    ok("2 items", len(review.items) == 2)

    # 矛盾应关联到「实验数据与结论」项（order_index=1）
    data_item = review.items[1]
    flags = data_item.review_flags or []
    has_contradiction = any(f.startswith("contradiction:") for f in flags)
    ok("contradiction linked to data item", has_contradiction)
    ok("data item needs_review", data_item.needs_review)

    for it in review.items:
        print(f"  item {it.order_index} flags={it.review_flags} needs_review={it.needs_review}", flush=True)

failed = [l for l, p in results if not p]
print("===", "ALL PASS" if not failed else f"FAILED: {failed}", "===")
sys.exit(1 if failed else 0)
