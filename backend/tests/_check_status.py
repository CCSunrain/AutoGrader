import os

os.environ["DATABASE_URL"] = "postgresql+psycopg://autograder:autograder@localhost:10080/autograder"

from app.core.db import SessionLocal  # noqa: E402
from app.models import BackgroundTask, Review  # noqa: E402
from sqlalchemy import text  # noqa: E402

with SessionLocal() as s:
    print("=== background_tasks 状态分布 ===")
    for row in s.execute(text("SELECT task_type, status, count(*) FROM background_tasks GROUP BY task_type, status ORDER BY task_type, status")):
        print(f"  {row[0]:<16} {row[1]:<10} {row[2]}")

    print("\n=== reviews 状态分布 ===")
    for row in s.execute(text("SELECT status, count(*) FROM reviews GROUP BY status")):
        print(f"  {row[0]:<16} {row[1]}")

    print("\n=== 最近 6 个任务 ===")
    for row in s.execute(text("SELECT task_type, status, attempts, lease_expires_at, created_at FROM background_tasks ORDER BY created_at DESC LIMIT 6")):
        print(f"  {row[0]:<16} {row[1]:<10} attempts={row[2]} lease={row[3]} created={row[4]}")

    print("\n=== 最近 6 个 review ===")
    for row in s.execute(text("SELECT status, model, created_at FROM reviews ORDER BY created_at DESC LIMIT 6")):
        print(f"  {row[0]:<16} model={row[1]} created={row[2]}")
