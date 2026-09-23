import os
import traceback

os.environ["DATABASE_URL"] = "postgresql+psycopg://autograder:autograder@localhost:5432/autograder"

from app.core.db import engine  # noqa: E402

try:
    with engine.connect() as conn:
        print("connected ok")
except BaseException:
    traceback.print_exc()
