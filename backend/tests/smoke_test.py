"""Standalone smoke test for the backend skeleton (uses SQLite).

Run from the repo root with the venv interpreter:
    backend/.venv/Scripts/python.exe backend/tests/smoke_test.py

Covers: health, register/login/me, tenant isolation, course CRUD,
rubric (nested items/bands) creation + version freeze, task enqueue.
"""
import os
import sys
import warnings

warnings.filterwarnings("ignore")

# 默认 SQLite 快速冒烟；也可从外部传入 DATABASE_URL 跑真实 PG 验证
os.environ.setdefault("DATABASE_URL", "sqlite:///./_smoke.db")

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: F401, E402
from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import BackgroundTask  # noqa: E402
from app.services.tasks import enqueue  # noqa: E402

Base.metadata.drop_all(bind=engine)  # reset any stale schema from a previous run
Base.metadata.create_all(bind=engine)
client = TestClient(app)

results: list[tuple[str, bool]] = []


def ok(label: str, cond: bool) -> bool:
    results.append((label, cond))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")
    return cond


# 1. health
r = client.get("/api/health")
ok("health", r.status_code == 200 and r.json()["status"] == "ok")

# 2. register two users (each gets an isolated workspace as owner)
r = client.post(
    "/api/auth/register",
    json={"email": "a@example.com", "username": "老师A", "password": "password123"},
)
ok("register A", r.status_code == 201)
token_a = r.json()["access_token"]

r = client.post(
    "/api/auth/register",
    json={"email": "b@example.com", "username": "老师B", "password": "password123"},
)
ok("register B", r.status_code == 201)
token_b = r.json()["access_token"]

# 3. login + me
r = client.post("/api/auth/login", json={"email": "a@example.com", "password": "password123"})
ok("login A", r.status_code == 200)

h_a = {"Authorization": f"Bearer {token_a}"}
h_b = {"Authorization": f"Bearer {token_b}"}

r = client.get("/api/auth/me", headers=h_a)
ok("me", r.status_code == 200 and r.json()["email"] == "a@example.com")

# 4. course CRUD + tenant isolation
r = client.post(
    "/api/courses",
    json={"name": "数据结构与算法", "code": "CS201", "term": "2026秋"},
    headers=h_a,
)
ok("create course", r.status_code == 201)
course_id = r.json()["id"]

r = client.get("/api/courses", headers=h_a)
ok("A sees 1 course", r.status_code == 200 and len(r.json()) == 1)

r = client.get("/api/courses", headers=h_b)
ok("tenant isolation (B sees 0)", r.status_code == 200 and len(r.json()) == 0)

r = client.get(f"/api/courses/{course_id}", headers=h_b)
ok("tenant isolation (B gets 404)", r.status_code == 404)

# 5. rubric (nested items + bands) + version freeze
rubric = {
    "title": "排序实验评分量表",
    "items": [
        {
            "name": "算法正确性",
            "max_score": 40,
            "order_index": 0,
            "bands": [
                {"level": "优秀", "score": 40, "order_index": 0},
                {"level": "良好", "score": 30, "order_index": 1},
                {"level": "及格", "score": 20, "order_index": 2},
            ],
        },
        {
            "name": "复杂度分析",
            "max_score": 30,
            "order_index": 1,
            "bands": [
                {"level": "优秀", "score": 30, "order_index": 0},
                {"level": "及格", "score": 15, "order_index": 1},
            ],
        },
    ],
}
r = client.post("/api/rubrics", json=rubric, headers=h_a)
ok("create rubric", r.status_code == 201)
rubric_id = r.json()["id"]
version0 = r.json()["versions"][0]
ok("rubric has 2 items", len(version0["items"]) == 2)
ok("item has 3 bands", len(version0["items"][0]["bands"]) == 3)

r = client.post(f"/api/rubrics/{rubric_id}/versions/{version0['id']}/freeze", headers=h_a)
ok("freeze version", r.status_code == 200 and r.json()["versions"][0]["frozen_at"] is not None)

# 6. task enqueue roundtrip
with SessionLocal() as s:
    t = enqueue(s, workspace_id="ws-test", task_type="noop", payload={"echo": "hi"})
    loaded = s.get(BackgroundTask, t.id)
ok("enqueue task", loaded is not None and loaded.task_type == "noop" and loaded.status == "pending")

failed = [label for label, passed in results if not passed]
print("===", "ALL PASS" if not failed else f"FAILED: {failed}", "===")
sys.exit(1 if failed else 0)
