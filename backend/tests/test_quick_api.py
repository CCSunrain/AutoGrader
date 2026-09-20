import os
import sys

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://autograder:autograder@localhost:10080/autograder"
)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)
ok_count = 0


def check(label, cond):
    global ok_count
    ok_count += 1 if cond else 0
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


r = client.post("/api/auth/login", json={"email": "teacher@x.com", "password": "password123"})
check("login", r.status_code == 200)
token = r.json()["access_token"]
h = {"Authorization": f"Bearer {token}"}

r = client.get("/api/courses", headers=h)
check("list courses", r.status_code == 200 and len(r.json()) > 0)
course_id = r.json()[0]["id"]

r = client.get(f"/api/courses/{course_id}/assignments", headers=h)
check("list assignments", r.status_code == 200 and len(r.json()) > 0)
assignment_id = r.json()[0]["id"]

r = client.get(f"/api/assignments/{assignment_id}/submissions", headers=h)
check("list submissions (new)", r.status_code == 200 and len(r.json()) > 0)

r = client.get("/api/rubrics", headers=h)
check("list rubrics", r.status_code == 200 and len(r.json()) > 0)
version_id = r.json()[0]["versions"][0]["id"]

r = client.get(f"/api/rubric-versions/{version_id}", headers=h)
check("get rubric version (new)", r.status_code == 200 and len(r.json()["items"]) > 0)

sub = client.get(f"/api/assignments/{assignment_id}/submissions", headers=h).json()[0]
vid = sub["versions"][-1]["id"]
r = client.get(f"/api/submission-versions/{vid}/reviews", headers=h)
check("list reviews (new)", r.status_code == 200 and len(r.json()) > 0)

r = client.get(f"/api/submission-versions/{vid}/parsed", headers=h)
check("get parsed", r.status_code == 200)

print(f"=== {ok_count}/8 passed ===")
sys.exit(0 if ok_count == 8 else 1)
