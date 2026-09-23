"""验证作业/量表/课程的编辑与删除 API（不调用 LLM）。"""
import os
import sys

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://autograder:autograder@localhost:10080/autograder"
)

from fastapi.testclient import TestClient  # noqa: E402

from app.core.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)
results: list[tuple[str, bool]] = []


def ok(label, cond):
    results.append((label, cond))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


r = client.post("/api/auth/register", json={"email": "t@x.com", "username": "老师", "password": "password123", "account_type": "teacher"})
h = {"Authorization": f"Bearer {r.json()['access_token']}"}

r = client.post("/api/courses", json={"name": "数据结构", "code": "CS101", "term": "2026秋"}, headers=h)
course_id = r.json()["id"]

r = client.post("/api/assignments", json={"course_id": course_id, "title": "排序实验"}, headers=h)
assignment_id = r.json()["id"]

r = client.post("/api/rubrics", json={"title": "量表A", "items": [{"name": "算法", "max_score": 10, "order_index": 0, "bands": [{"level": "优秀", "score": 10, "order_index": 0}]}]}, headers=h)
rubric_id = r.json()["id"]

# 1. PATCH 作业
r = client.patch(f"/api/assignments/{assignment_id}", json={"title": "排序实验（改）", "description": "新说明"}, headers=h)
ok("patch assignment", r.status_code == 200 and r.json()["title"] == "排序实验（改）")

# 2. DELETE 量表
r = client.delete(f"/api/rubrics/{rubric_id}", headers=h)
ok("delete rubric", r.status_code == 204)
r = client.get(f"/api/rubrics/{rubric_id}", headers=h)
ok("rubric gone", r.status_code == 404)

# 3. DELETE 作业
r = client.delete(f"/api/assignments/{assignment_id}", headers=h)
ok("delete assignment", r.status_code == 204)
r = client.get(f"/api/courses/{course_id}/assignments", headers=h)
ok("assignment gone", len(r.json()) == 0)

# 4. PATCH 课程
r = client.patch(f"/api/courses/{course_id}", json={"name": "数据结构（改）"}, headers=h)
ok("patch course", r.status_code == 200 and r.json()["name"] == "数据结构（改）")

failed = [l for l, p in results if not p]
print("===", "ALL PASS" if not failed else f"FAILED: {failed}", "===")
sys.exit(1 if failed else 0)
