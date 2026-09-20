"""Background worker entrypoint.

A standalone process that polls the `background_tasks` table, claims rows with
`FOR UPDATE SKIP LOCKED`, and executes the matching handler. Tasks persist in
PostgreSQL, so a crash only delays work until the lease expires and the row is
re-claimed — this implements the "persistent task + resume" requirement.

Run with:  python -m app.worker.main
"""
import time
from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.core.db import SessionLocal
from app.core.logging import get_logger, setup_logging
from app.models import (
    BackgroundTask,
    ParsedDocument,
    Review,
    RubricBand,
    RubricItem,
    RubricVersion,
    SubmissionVersion,
)
from app.models.base import utcnow
from app.services import storage
from app.services.grading.engine import run_review
from app.services.parsers.registry import parse_document

setup_logging()
logger = get_logger("autograder.worker")

LEASE_SECONDS = 600  # a running task holds a lease this long
POLL_SECONDS = 2
RETRY_DELAY_SECONDS = 30  # cooldown before a failed task is retried

# task_type -> handler(payload: dict) -> dict result
TASK_HANDLERS: dict[str, callable] = {}


def register(task_type: str):
    def deco(fn):
        TASK_HANDLERS[task_type] = fn
        return fn

    return deco


@register("noop")
def handle_noop(payload: dict) -> dict:
    return {"ok": True, "echo": payload.get("echo")}


@register("parse_document")
def handle_parse_document(payload: dict) -> dict:
    version_id = payload.get("submission_version_id")
    parsed_id = payload.get("parsed_document_id")
    if not version_id or not parsed_id:
        raise ValueError("missing submission_version_id / parsed_document_id")

    with SessionLocal() as session:
        version = session.get(SubmissionVersion, version_id)
        if version is None:
            raise ValueError(f"submission version not found: {version_id}")
        parsed = session.get(ParsedDocument, parsed_id)
        if parsed is None:
            raise ValueError(f"parsed document not found: {parsed_id}")

        data = storage.read_upload(version.file_key)
        result = parse_document(data, version.content_type, version.filename)

        parsed.parser_version = result.parser_version
        parsed.raw_text = result.raw_text
        parsed.content = result.to_dict()
        parsed.status = "done"
        parsed.error = ""
        session.commit()
        logger.info(
            "解析完成 version=%s type=%s blocks=%d chars=%d",
            version_id,
            version.content_type,
            len(result.blocks),
            len(result.raw_text),
        )
        return {
            "status": "done",
            "submission_version_id": version_id,
            "blocks": len(result.blocks),
            "page_count": result.page_count,
        }


@register("run_review")
def handle_run_review(payload: dict) -> dict:
    review_id = payload.get("review_id")
    if not review_id:
        raise ValueError("missing review_id")

    with SessionLocal() as session:
        review = session.get(Review, review_id)
        if review is None:
            raise ValueError(f"review not found: {review_id}")

        # 幂等：已评阅完成则跳过（防止重复处理导致 ReviewItem 翻倍）
        if review.status in ("done", "published"):
            return {"status": "skipped", "review_id": review_id}

        rubric_version = (
            session.query(RubricVersion)
            .options(selectinload(RubricVersion.items).selectinload(RubricItem.bands))
            .filter(RubricVersion.id == review.rubric_version_id)
            .first()
        )
        if rubric_version is None:
            raise ValueError(f"rubric version not found: {review.rubric_version_id}")

        parsed = (
            session.query(ParsedDocument)
            .filter(
                ParsedDocument.submission_version_id == review.submission_version_id,
                ParsedDocument.status == "done",
            )
            .first()
        )
        if parsed is None:
            raise ValueError("报告解析未完成，无法评阅")

        review.status = "running"
        session.commit()

        logger.info("开始评阅 review=%s rubric_version=%s", review_id, review.rubric_version_id)
        run_review(session, review, rubric_version, parsed)
        session.commit()

        logger.info(
            "评阅完成 review=%s items=%d 矛盾=%d",
            review_id,
            len(review.items),
            len(review.contradictions or []),
        )
        return {"status": "done", "review_id": review_id, "items": len(review.items)}


def claim_task(session) -> BackgroundTask | None:
    now = utcnow()
    stmt = (
        select(BackgroundTask)
        .where(
            BackgroundTask.status.in_(["pending", "retry"]),
            or_(
                BackgroundTask.lease_expires_at.is_(None),
                BackgroundTask.lease_expires_at < now,
            ),
        )
        .order_by(BackgroundTask.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    task = session.execute(stmt).scalar_one_or_none()
    if task is None:
        return None
    task.status = "running"
    task.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
    task.attempts += 1
    task.started_at = now
    session.commit()
    return task


def _finish(task_id: str, result: dict) -> None:
    with SessionLocal() as session:
        task = session.get(BackgroundTask, task_id)
        if task is None:
            return
        task.status = "succeeded"
        task.result = result or {}
        task.finished_at = utcnow()
        task.lease_expires_at = None
        session.commit()


def _fail(task_id: str, error: str) -> None:
    with SessionLocal() as session:
        task = session.get(BackgroundTask, task_id)
        if task is None:
            return
        task.error = error
        if task.attempts >= task.max_attempts:
            task.status = "failed"
            task.lease_expires_at = None
            task.finished_at = utcnow()
        else:
            task.status = "retry"
            # cooldown: don't let the same failed task be re-claimed immediately
            task.lease_expires_at = utcnow() + timedelta(seconds=RETRY_DELAY_SECONDS)
        session.commit()


def loop() -> None:
    logger.info("worker started")
    while True:
        claimed: tuple[str, str, dict] | None = None
        try:
            with SessionLocal() as session:
                task = claim_task(session)
                if task is not None:
                    claimed = (task.id, task.task_type, dict(task.payload or {}))
        except Exception:  # noqa: BLE001 - keep the loop alive on transient DB errors
            logger.exception("claim failed")
            time.sleep(POLL_SECONDS)
            continue

        if claimed is None:
            time.sleep(POLL_SECONDS)
            continue

        task_id, task_type, payload = claimed
        handler = TASK_HANDLERS.get(task_type)
        try:
            if handler is None:
                raise ValueError(f"unknown task type: {task_type}")
            logger.info("running %s %s", task_type, task_id)
            result = handler(payload)
            _finish(task_id, result)
            logger.info("done %s", task_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("failed %s: %s", task_id, exc)
            _fail(task_id, str(exc))


if __name__ == "__main__":
    loop()
