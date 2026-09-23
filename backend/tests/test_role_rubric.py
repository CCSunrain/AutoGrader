"""验证角色定位（教师/学生）+ 量表编辑，不调用 LLM。

Run:  PYTHONPATH= uv run --project backend python backend/tests/test_role_rubric.py
"""
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
    return cond


RUBRIC_V1 = {
    "title": "排序量表",
    "items": [
        {"name": "算法正确性", "max_score": 40, "order_index": 0,
         "bands": [{"level": "优秀", "score": 40, "order_index": 0}, {"level": "不及格", "score": 0, "order_index": 1}]},
        {"name": "复杂度分析", "max_score": 30, "order_index": 1,
         "bands": [{"level": "优秀", "score": 30, "order_index": 0}, {"level": "不及格", "score": 0, "order_index": 1}]},
    ],
}

RUBRIC_V2 = {
    "title": "排序量表（修订）",
    "items": [
        {"name": "算法实现正确性", "max_score": 50, "order_index": 0,
         "bands": [{"level": "优秀", "score": 50, "order_index": 0}, {"level": "及格", "score": 25, "order_index": 1}, {"level": "不及格", "score": 0, "order_index": 2}]},
    ],
}

# 1. 教师注册 + 建课程（生成 join_code）
r = client.post("/api/auth/register", json={"email": "t@x.com", "username": "老师", "password": "password123", "account_type": "teacher"})
ok("teacher register", r.status_code == 201)
ok("teacher account_type", r.json()["user"]["account_type"] == "teacher")
teacher_h = {"Authorization": f"Bearer {r.json()['access_token']}"}

r = client.post("/api/courses", json={"name": "数据结构", "code": "CS101", "term": "2026秋"}, headers=teacher_h)
ok("create course", r.status_code == 201)
course = r.json()
join_code = course["join_code"]
course_ws = course["workspace_id"]
ok("has join_code", bool(join_code))

r = client.post("/api/assignments", json={"course_id": course["id"], "title": "排序实验"}, headers=teacher_h)
assignment_id = r.json()["id"]

# 2. 学生注册 + 加入课程
r = client.post("/api/auth/register", json={"email": "s@x.com", "username": "小明", "password": "password123", "account_type": "student"})
ok("student register", r.status_code == 201)
ok("student account_type", r.json()["user"]["account_type"] == "student")
student_h = {"Authorization": f"Bearer {r.json()['access_token']}"}
student_id = r.json()["user"]["id"]

r = client.post("/api/courses/join", json={"code": join_code}, headers=student_h)
ok("student join course", r.status_code == 200)

# 学生视角（切到教师 workspace）
sh = {"Authorization": student_h["Authorization"], "X-Workspace-Id": course_ws}
r = client.get("/api/courses/mine", headers=sh)
ok("student sees joined course", any(c["id"] == course["id"] for c in r.json()))

# 3. 学生上传自己的报告（不传 student_id，后端用本人）
r = client.post(
    f"/api/assignments/{assignment_id}/submissions",
    files={"file": ("r.md", b"# report", "text/markdown")},
    headers=sh,
)
ok("student upload", r.status_code == 201)
ok("upload uses own id", r.json()["student_id"] == student_id)

# 学生只能看到自己的提交
r = client.get(f"/api/assignments/{assignment_id}/submissions", headers=sh)
ok("student sees only own submissions", len(r.json()) == 1)

# 4. 量表编辑：未冻结时更新当前版本
r = client.post("/api/rubrics", json=RUBRIC_V1, headers=teacher_h)
ok("create rubric", r.status_code == 201)
rubric_id = r.json()["id"]
v1_id = r.json()["versions"][0]["id"]

r = client.put(f"/api/rubrics/{rubric_id}", json=RUBRIC_V2, headers=teacher_h)
ok("update rubric (unfrozen)", r.status_code == 200)
ok("still 1 version", len(r.json()["versions"]) == 1)
ok("items updated", r.json()["versions"][0]["items"][0]["name"] == "算法实现正确性")

# 冻结后再编辑 → 新建版本
r = client.post(f"/api/rubrics/{rubric_id}/versions/{v1_id}/freeze", headers=teacher_h)
ok("freeze", r.status_code == 200)
r = client.put(f"/api/rubrics/{rubric_id}", json=RUBRIC_V1, headers=teacher_h)
ok("update after freeze", r.status_code == 200)
ok("new version created", len(r.json()["versions"]) == 2)

# 学生不能建量表（权限）
r = client.post("/api/rubrics", json=RUBRIC_V1, headers=sh)
ok("student cannot create rubric", r.status_code == 403)

failed = [l for l, p in results if not p]
print("===", "ALL PASS" if not failed else f"FAILED: {failed}", "===")
sys.exit(1 if failed else 0)
