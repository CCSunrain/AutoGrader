import os
import sys

print("step0", flush=True)
os.environ["DATABASE_URL"] = "postgresql+psycopg://autograder:autograder@localhost:5432/autograder"
print("step1", flush=True)

from app.core.db import Base, engine  # noqa: E402
print("step2", flush=True)

from sqlalchemy import text  # noqa: E402
print("step3", flush=True)

with engine.connect() as conn:
    print("step4 connected", flush=True)
    print("SELECT 1 =", conn.execute(text("SELECT 1")).scalar(), flush=True)
