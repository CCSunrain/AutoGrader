"""第二模板（最短路径实验）端到端验证：跑通上传→解析→评阅→复核→发布。

Run:  PYTHONPATH= uv run --project backend python backend/tests/test_shortest_path_e2e.py
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


def ok(label, cond):
    results.append((label, cond))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")
    return cond


# 1. register + course + assignment + 最短路径量表
r = client.post(
    "/api/auth/register", json={"email": "t2@x.com", "username": "教师", "password": "password123"}
)
token = r.json()["access_token"]
h = {"Authorization": f"Bearer {token}"}

r = client.post("/api/courses", json={"name": "数据结构", "code": "CS102", "term": "2026秋"}, headers=h)
course_id = r.json()["id"]
r = client.post("/api/assignments", json={"course_id": course_id, "title": "最短路径算法实验"}, headers=h)
assignment_id = r.json()["id"]

rubric = {
    "title": "最短路径算法实验评分量表",
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
        {"name": "实验数据与结论", "max_score": 30, "order_index": 2,
         "bands": [
             {"level": "优秀", "score": 30, "order_index": 0},
             {"level": "良好", "score": 20, "order_index": 1},
             {"level": "及格", "score": 10, "order_index": 2},
             {"level": "不及格", "score": 0, "order_index": 3},
         ]},
    ],
}
r = client.post("/api/rubrics", json=rubric, headers=h)
ok("create shortest-path rubric", r.status_code == 201)
rubric_version_id = r.json()["versions"][0]["id"]

# 2. upload 最短路径报告
REPORT = """# 最短路径算法实验报告

## 算法实现

本实验实现了 Dijkstra 算法求解单源最短路径，使用优先队列（二叉堆）优化。

```python
import heapq

def dijkstra(graph, start):
    dist = {node: float('inf') for node in graph}
    dist[start] = 0
    pq = [(0, start)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        for v, w in graph[u]:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                heapq.heappush(pq, (dist[v], v))
    return dist
```

## 复杂度分析

使用二叉堆优先队列，时间复杂度为 O((V+E) log V)，空间复杂度为 O(V)。

## 实验结果

| 节点数 | 边数 | 运行时间(ms) |
| --- | --- | --- |
| 100 | 500 | 2.1 |
| 1000 | 5000 | 45.6 |
| 10000 | 50000 | 890.3 |
"""
r = client.post(
    f"/api/assignments/{assignment_id}/submissions",
    files={"file": ("dijkstra.md", REPORT.encode(), "text/markdown")},
    data={"student_id": "stu-dj"},
    headers=h,
)
ok("upload shortest-path report", r.status_code == 201)
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

# 4. verify + decide + publish
with SessionLocal() as s:
    review = s.get(Review, review_id)
    ok("review done", review.status == "done")
    ok("3 items", len(review.items) == 3)
    for it in review.items:
        ok(f"item {it.order_index} state valid", it.evidence_state in ("supported", "missing", "uncertain"))

    # 对每项给"优秀"档，发布
    band_map = {it.name: {b.level: b.id for b in it.bands} for it in s.query(models.RubricItem).all()}
    for it in review.items:
        rub = s.get(models.RubricItem, it.rubric_item_id)
        bid = band_map[rub.name]["优秀"]
        r = client.post(
            f"/api/review-items/{it.id}/decision",
            json={"final_band_id": bid, "feedback": "通过"},
            headers=h,
        )
        if r.status_code != 200:
            ok(f"decide item {it.order_index}", False)
            continue

r = client.post(f"/api/reviews/{review_id}/publish", json={"feedback": "最短路径实验完成良好"}, headers=h)
ok("publish", r.status_code == 200)
ok("score = 100", r.json()["publish"]["score"] == 100)

failed = [l for l, p in results if not p]
print("===", "ALL PASS" if not failed else f"FAILED: {failed}", "===")
sys.exit(1 if failed else 0)
