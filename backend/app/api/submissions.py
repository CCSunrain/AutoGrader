"""Submission upload / query endpoints (tenant-isolated, role-aware)."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.core.deps import AuthContext, get_auth_context
from app.core.roles import Role
from app.models import Assignment, ParsedDocument, Review, Submission, SubmissionVersion, User
from app.schemas.submission import ParsedDocumentOut, SubmissionOut, VersionCompareOut, VersionSummary
from app.services import storage
from app.services.tasks import enqueue

router = APIRouter(tags=["submissions"])

_STAFF = (Role.OWNER, Role.TEACHER, Role.TA)
_ALLOWED_EXT = {"pdf": "pdf", "md": "markdown", "markdown": "markdown"}
_MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


def _content_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _ALLOWED_EXT:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"不支持的文件类型: {ext}")
    return _ALLOWED_EXT[ext]


def _load_submission(db: Session, submission_id: str, workspace_id: str) -> Submission:
    submission = (
        db.query(Submission)
        .options(selectinload(Submission.versions))
        .filter(Submission.id == submission_id, Submission.workspace_id == workspace_id)
        .first()
    )
    if submission is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "提交不存在")
    return submission


def _fill_student_names(db: Session, submissions: list[Submission]) -> None:
    """Fill each submission's `student_name` from the User table (fallback to student_id)."""
    ids = list({s.student_id for s in submissions if s.student_id})
    if not ids:
        return
    name_map = {
        uid: uname for uid, uname in db.query(User.id, User.username).filter(User.id.in_(ids)).all()
    }
    for s in submissions:
        s.student_name = name_map.get(s.student_id) or s.student_id


@router.post(
    "/assignments/{assignment_id}/submissions",
    response_model=SubmissionOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_submission(
    assignment_id: str,
    file: UploadFile = File(...),
    student_id: str | None = Form(default=None),
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    assignment = (
        db.query(Assignment)
        .filter(Assignment.id == assignment_id, Assignment.workspace_id == ctx.workspace_id)
        .first()
    )
    if assignment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "作业不存在")

    # 教师/助教可代传（需指定 student_id）；学生只能传本人
    if ctx.role in _STAFF and student_id:
        target_student = student_id
    else:
        target_student = ctx.user.id

    content_type = _content_type(file.filename or "")
    data = file.file.read()
    if len(data) > _MAX_FILE_SIZE:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "文件超过 20MB 上限")

    submission = (
        db.query(Submission)
        .filter(
            Submission.assignment_id == assignment_id,
            Submission.student_id == target_student,
            Submission.workspace_id == ctx.workspace_id,
        )
        .first()
    )
    if submission is None:
        submission = Submission(
            workspace_id=ctx.workspace_id,
            assignment_id=assignment_id,
            student_id=target_student,
            status="submitted",
        )
        db.add(submission)
        db.flush()

    max_no = (
        db.execute(
            select(func.max(SubmissionVersion.version_no)).where(
                SubmissionVersion.submission_id == submission.id
            )
        ).scalar()
        or 0
    )
    version = SubmissionVersion(
        workspace_id=ctx.workspace_id,
        submission_id=submission.id,
        version_no=max_no + 1,
        filename=file.filename or "report",
        content_type=content_type,
        file_key="",
        created_by=ctx.user.id,
    )
    db.add(version)
    db.flush()

    ext = "." + (file.filename.rsplit(".", 1)[-1] if "." in (file.filename or "") else "bin")
    version.file_key = storage.save_upload(
        workspace_id=ctx.workspace_id, file_id=version.id, ext=ext, content=data
    )

    parsed = ParsedDocument(
        workspace_id=ctx.workspace_id,
        submission_version_id=version.id,
        parser_version="",
        status="pending",
    )
    db.add(parsed)
    db.commit()

    # 入队解析任务（worker 异步执行）
    enqueue(
        db,
        workspace_id=ctx.workspace_id,
        task_type="parse_document",
        payload={"submission_version_id": version.id, "parsed_document_id": parsed.id},
    )

    result = _load_submission(db, submission.id, ctx.workspace_id)
    _fill_student_names(db, [result])
    return result


@router.get("/assignments/{assignment_id}/submissions", response_model=list[SubmissionOut])
def list_submissions(
    assignment_id: str,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Submission)
        .options(selectinload(Submission.versions))
        .filter(
            Submission.assignment_id == assignment_id,
            Submission.workspace_id == ctx.workspace_id,
        )
    )
    # 学生只能看到本人的提交
    if ctx.role == Role.STUDENT:
        query = query.filter(Submission.student_id == ctx.user.id)
    submissions = query.order_by(Submission.created_at.desc()).all()
    _fill_student_names(db, submissions)
    return submissions


@router.get("/submissions/{submission_id}", response_model=SubmissionOut)
def get_submission(
    submission_id: str,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    submission = _load_submission(db, submission_id, ctx.workspace_id)
    # 学生只能看本人的提交
    if ctx.role == Role.STUDENT and submission.student_id != ctx.user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "无权查看他人提交")
    _fill_student_names(db, [submission])
    return submission


@router.get("/submission-versions/{version_id}/parsed", response_model=ParsedDocumentOut)
def get_parsed(
    version_id: str,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    parsed = (
        db.query(ParsedDocument)
        .filter(
            ParsedDocument.submission_version_id == version_id,
            ParsedDocument.workspace_id == ctx.workspace_id,
        )
        .first()
    )
    if parsed is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "解析记录不存在")
    return parsed


@router.get(
    "/submissions/{submission_id}/compare/{from_version_id}/{to_version_id}",
    response_model=VersionCompareOut,
)
def compare_versions(
    submission_id: str,
    from_version_id: str,
    to_version_id: str,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    submission = db.get(Submission, submission_id)
    if submission is None or submission.workspace_id != ctx.workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "提交不存在")
    if ctx.role == Role.STUDENT and submission.student_id != ctx.user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "无权查看他人提交")

    versions = (
        db.query(SubmissionVersion)
        .filter(
            SubmissionVersion.id.in_([from_version_id, to_version_id]),
            SubmissionVersion.submission_id == submission_id,
        )
        .all()
    )
    by_id = {v.id: v for v in versions}
    if from_version_id not in by_id or to_version_id not in by_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "版本不存在")

    def summary(version: SubmissionVersion) -> VersionSummary:
        parsed = (
            db.query(ParsedDocument)
            .filter(ParsedDocument.submission_version_id == version.id, ParsedDocument.status == "done")
            .first()
        )
        score: float | None = None
        feedback = ""
        review = (
            db.query(Review)
            .filter(Review.submission_version_id == version.id, Review.status == "published")
            .first()
        )
        if review is not None and review.publish is not None:
            score = review.publish.score
            feedback = review.publish.feedback
        return VersionSummary(
            version_id=version.id,
            version_no=version.version_no,
            raw_text=parsed.raw_text if parsed else "",
            score=score,
            feedback=feedback,
        )

    frm = summary(by_id[from_version_id])
    to = summary(by_id[to_version_id])
    delta = (to.score - frm.score) if (to.score is not None and frm.score is not None) else None
    return VersionCompareOut(from_version=frm, to_version=to, score_delta=delta)
