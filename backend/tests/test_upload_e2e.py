"""End-to-end test: upload (PDF + Markdown) -> parse, against real PostgreSQL.

Run:  PYTHONPATH= uv run --project backend python backend/tests/test_upload_e2e.py
"""
import io
import os
import sys
import uuid

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://autograder:autograder@localhost:10080/autograder"
)

import fitz  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: F401, E402
from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import ParsedDocument  # noqa: E402
from app.worker.main import handle_parse_document  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)

results: list[tuple[str, bool]] = []


def ok(label: str, cond: bool) -> bool:
    results.append((label, cond))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")
    return cond


def _make_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Sorting Algorithm Report")
    page.insert_text((72, 100), "Quick sort, time complexity O(n log n).")
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


suffix = uuid.uuid4().hex[:8]

# 1. register teacher + create course/assignment
r = client.post(
    "/api/auth/register",
    json={"email": f"t-{suffix}@x.com", "username": "教师", "password": "password123"},
)
ok("register teacher", r.status_code == 201)
token = r.json()["access_token"]
h = {"Authorization": f"Bearer {token}"}

r = client.post("/api/courses", json={"name": "数据结构", "code": f"CS{suffix}", "term": "2026秋"}, headers=h)
ok("create course", r.status_code == 201)
course_id = r.json()["id"]

r = client.post(
    "/api/assignments",
    json={"course_id": course_id, "title": "排序算法实验", "description": "实现并分析排序算法"},
    headers=h,
)
ok("create assignment", r.status_code == 201)
assignment_id = r.json()["id"]


def upload_and_parse(label: str, filename: str, content: bytes, mime: str) -> str:
    r = client.post(
        f"/api/assignments/{assignment_id}/submissions",
        files={"file": (filename, content, mime)},
        data={"student_id": f"stu-{suffix}"},
        headers=h,
    )
    ok(f"upload {label}", r.status_code == 201)
    version_id = r.json()["versions"][-1]["id"]

    with SessionLocal() as s:
        parsed = s.query(ParsedDocument).filter_by(submission_version_id=version_id).first()
        parsed_id = parsed.id
        ok(f"{label} parsed=pending before worker", parsed.status == "pending")

    result = handle_parse_document(
        {"submission_version_id": version_id, "parsed_document_id": parsed_id}
    )

    with SessionLocal() as s:
        parsed = s.get(ParsedDocument, parsed_id)
        ok(f"{label} parsed=done", parsed.status == "done")
        ok(f"{label} has blocks", len(parsed.content.get("blocks", [])) > 0)
        ok(f"{label} has raw_text", len(parsed.raw_text) > 0)
        return parsed_id


MARKDOWN = """# 排序算法实验报告

## 算法实现

使用快速排序，时间复杂度 O(n log n)。

```python
def quicksort(arr):
    return sorted(arr)
```

| 数据规模 | 运行时间 |
| --- | --- |
| 1000 | 0.01s |
| 10000 | 0.12s |
"""

upload_and_parse("markdown", "report.md", MARKDOWN.encode("utf-8"), "text/markdown")
upload_and_parse("pdf", "report.pdf", _make_pdf(), "application/pdf")

failed = [l for l, p in results if not p]
print("===", "ALL PASS" if not failed else f"FAILED: {failed}", "===")
sys.exit(1 if failed else 0)
