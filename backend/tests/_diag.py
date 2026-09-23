import os
import traceback

os.environ["DATABASE_URL"] = "postgresql+psycopg://autograder:autograder@localhost:5432/autograder"

from app.core.db import Base, engine  # noqa: E402
from sqlalchemy import text  # noqa: E402

print("1. connecting...")
with engine.connect() as conn:
    print("2. connected, SELECT 1 =", conn.execute(text("SELECT 1")).scalar())

print("3. dropping...")
try:
    Base.metadata.drop_all(bind=engine)
    print("4. drop ok")
except BaseException as e:
    print("DROP FAILED:", type(e).__name__, e)
    traceback.print_exc()
