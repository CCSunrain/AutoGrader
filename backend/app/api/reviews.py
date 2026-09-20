"""Review endpoints: review, human decision, publish, and student view.

Core product guarantees enforced here:
- Only owner/teacher can publish the final grade.
- Published reviews are immutable; corrections require a new review revision.
- AI only suggests — the published score is computed from human decisions.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.core.deps import AuthContext, get_auth_context, require_roles
from app.core.roles import Role
from app.models import (
    HumanDecision,
    PublishRecord,
    Review,
    ReviewItem,
    RubricBand,
    RubricItem,
    RubricVersion,
    Submission,
    SubmissionVersion,
)
from app.models.base import utcnow
from app.schemas.review import (
    DecisionCreate,
    PublishCreate,
    PublishedItemOut,
    PublishedOut,
    ReviewCreate,
    ReviewOut,
)
from app.schemas.rubric import VersionOut
from app.services.tasks import enqueue

router = APIRouter(tags=["reviews"])

_STAFF = require_roles(Role.OWNER, Role.TEACHER, Role.TA)
_PUBLISHERS = require_roles(Role.OWNER, Role.TEACHER)


def _load_review(db: Session, review_id: str, workspace_id: str) -> Review:
    review = (
        db.query(Review)
        .options(
            selectinload(Review.items).selectinload(ReviewItem.evidences),
            selectinload(Review.items).selectinload(ReviewItem.decisions),
            selectinload(Review.publish_records),
        )
        .filter(Review.id == review_id, Review.workspace_id == workspace_id)
        .first()
    )
    if review is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "评阅不存在")
    return review


@router.post(
    "/submission-versions/{version_id}/reviews",
    response_model=ReviewOut,
    status_code=status.HTTP_201_CREATED,
)
def create_review(
    version_id: str,
    payload: ReviewCreate,
    ctx: AuthContext = Depends(_STAFF),
    db: Session = Depends(get_db),
):
    version = (
        db.query(SubmissionVersion)
        .filter(SubmissionVersion.id == version_id, SubmissionVersion.workspace_id == ctx.workspace_id)
        .first()
    )
    if version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "提交版本不存在")

    rubric_version = (
        db.query(RubricVersion)
        .filter(
            RubricVersion.id == payload.rubric_version_id,
            RubricVersion.workspace_id == ctx.workspace_id,
        )
        .first()
    )
    if rubric_version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "量表版本不存在")

    review = Review(
        workspace_id=ctx.workspace_id,
        submission_version_id=version_id,
        rubric_version_id=payload.rubric_version_id,
        status="pending",
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    enqueue(
        db,
        workspace_id=ctx.workspace_id,
        task_type="run_review",
        payload={"review_id": review.id},
    )
    return _load_review(db, review.id, ctx.workspace_id)


@router.get("/reviews/{review_id}", response_model=ReviewOut)
def get_review(
    review_id: str,
    ctx: AuthContext = Depends(require_roles(Role.OWNER, Role.TEACHER, Role.TA)),
    db: Session = Depends(get_db),
):
    return _load_review(db, review_id, ctx.workspace_id)


@router.get("/rubric-versions/{version_id}", response_model=VersionOut)
def get_rubric_version(
    version_id: str,
    ctx: AuthContext = Depends(require_roles(Role.OWNER, Role.TEACHER, Role.TA)),
    db: Session = Depends(get_db),
):
    version = (
        db.query(RubricVersion)
        .options(selectinload(RubricVersion.items).selectinload(RubricItem.bands))
        .filter(RubricVersion.id == version_id, RubricVersion.workspace_id == ctx.workspace_id)
        .first()
    )
    if version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "量表版本不存在")
    return version


@router.get("/submission-versions/{version_id}/reviews", response_model=list[ReviewOut])
def list_reviews(
    version_id: str,
    ctx: AuthContext = Depends(require_roles(Role.OWNER, Role.TEACHER, Role.TA)),
    db: Session = Depends(get_db),
):
    return (
        db.query(Review)
        .options(
            selectinload(Review.items).selectinload(ReviewItem.evidences),
            selectinload(Review.items).selectinload(ReviewItem.decisions),
            selectinload(Review.publish_records),
        )
        .filter(Review.submission_version_id == version_id, Review.workspace_id == ctx.workspace_id)
        .order_by(Review.created_at.desc())
        .all()
    )


@router.post("/review-items/{review_item_id}/decision", response_model=ReviewOut)
def submit_decision(
    review_item_id: str,
    payload: DecisionCreate,
    ctx: AuthContext = Depends(_STAFF),
    db: Session = Depends(get_db),
):
    item = (
        db.query(ReviewItem)
        .filter(ReviewItem.id == review_item_id, ReviewItem.workspace_id == ctx.workspace_id)
        .first()
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "评分项不存在")

    review = db.get(Review, item.review_id)
    if review.status == "published":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "已发布的评阅不可修改，请发起新的评阅修订"
        )

    band = db.get(RubricBand, payload.final_band_id)
    if band is None or band.rubric_item_id != item.rubric_item_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "档位不属于该评分项")

    decision = HumanDecision(
        workspace_id=ctx.workspace_id,
        review_item_id=review_item_id,
        reviewer_id=ctx.user.id,
        final_band_id=payload.final_band_id,
        feedback=payload.feedback,
    )
    item.decisions.append(decision)  # keep the cached relationship in sync
    db.commit()
    return _load_review(db, item.review_id, ctx.workspace_id)


@router.post("/reviews/{review_id}/publish", response_model=ReviewOut)
def publish_review(
    review_id: str,
    payload: PublishCreate,
    ctx: AuthContext = Depends(_PUBLISHERS),
    db: Session = Depends(get_db),
):
    review = _load_review(db, review_id, ctx.workspace_id)
    if review.status == "published":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "已发布，不可重复发布")
    if review.status != "done":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "评阅尚未完成，无法发布")

    total = 0.0
    for item in review.items:
        decision = item.decision
        if decision is None or decision.final_band_id is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"评分项 {item.order_index + 1} 尚未复核，无法发布"
            )
        band = db.get(RubricBand, decision.final_band_id)
        total += band.score

    record = PublishRecord(
        workspace_id=ctx.workspace_id,
        review_id=review_id,
        published_by=ctx.user.id,
        published_at=utcnow(),
        score=total,
        feedback=payload.feedback,
    )
    review.publish_records.append(record)  # keep the cached relationship in sync
    review.status = "published"
    db.commit()
    return _load_review(db, review_id, ctx.workspace_id)


@router.get("/submissions/{submission_id}/published", response_model=PublishedOut)
def get_published(
    submission_id: str,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    submission = db.get(Submission, submission_id)
    if submission is None or submission.workspace_id != ctx.workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "提交不存在")
    if ctx.role == Role.STUDENT and submission.student_id != ctx.user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "无权查看他人结果")

    version_ids = [v.id for v in submission.versions]
    review = (
        db.query(Review)
        .filter(
            Review.submission_version_id.in_(version_ids),
            Review.workspace_id == ctx.workspace_id,
            Review.status == "published",
        )
        .order_by(Review.created_at.desc())
        .first()
    )
    if review is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "暂无已发布结果")

    publish = review.publish
    version = db.get(SubmissionVersion, review.submission_version_id)

    items_out: list[PublishedItemOut] = []
    for item in sorted(review.items, key=lambda x: x.order_index):
        decision = item.decision
        rubric_item = db.get(RubricItem, item.rubric_item_id)
        level, score = "", 0
        if decision and decision.final_band_id:
            band = db.get(RubricBand, decision.final_band_id)
            if band:
                level, score = band.level, band.score
        items_out.append(
            PublishedItemOut(
                rubric_item_name=rubric_item.name if rubric_item else "",
                final_band_level=level,
                score=score,
                feedback=decision.feedback if decision else "",
            )
        )

    return PublishedOut(
        submission_id=submission_id,
        version_no=version.version_no if version else 0,
        score=publish.score,
        feedback=publish.feedback,
        published_at=publish.published_at,
        items=items_out,
    )
