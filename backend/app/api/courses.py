"""Course and assignment endpoints (all tenant-isolated)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import AuthContext, get_auth_context, require_roles
from app.core.roles import Role
from app.models import Assignment, Course, Review, RubricBand, RubricItem, Submission
from app.schemas.course import (
    AssignmentCreate,
    AssignmentOut,
    AssignmentStatsOut,
    CourseCreate,
    CourseOut,
    CourseUpdate,
    ItemAvg,
)

router = APIRouter(tags=["courses"])

# permissions: owners and teachers manage courses; everyone can view
_MANAGE = require_roles(Role.OWNER, Role.TEACHER)


@router.get("/courses", response_model=list[CourseOut])
def list_courses(
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    return (
        db.query(Course)
        .filter(Course.workspace_id == ctx.workspace_id)
        .order_by(Course.created_at.desc())
        .all()
    )


@router.post("/courses", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate,
    ctx: AuthContext = Depends(_MANAGE),
    db: Session = Depends(get_db),
):
    course = Course(workspace_id=ctx.workspace_id, **payload.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.get("/courses/{course_id}", response_model=CourseOut)
def get_course(
    course_id: str,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    course = (
        db.query(Course)
        .filter(Course.id == course_id, Course.workspace_id == ctx.workspace_id)
        .first()
    )
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "课程不存在")
    return course


@router.patch("/courses/{course_id}", response_model=CourseOut)
def update_course(
    course_id: str,
    payload: CourseUpdate,
    ctx: AuthContext = Depends(_MANAGE),
    db: Session = Depends(get_db),
):
    course = (
        db.query(Course)
        .filter(Course.id == course_id, Course.workspace_id == ctx.workspace_id)
        .first()
    )
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "课程不存在")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(course, field, value)
    db.commit()
    db.refresh(course)
    return course


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: str,
    ctx: AuthContext = Depends(_MANAGE),
    db: Session = Depends(get_db),
):
    course = (
        db.query(Course)
        .filter(Course.id == course_id, Course.workspace_id == ctx.workspace_id)
        .first()
    )
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "课程不存在")
    db.delete(course)
    db.commit()


@router.post("/assignments", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: AssignmentCreate,
    ctx: AuthContext = Depends(_MANAGE),
    db: Session = Depends(get_db),
):
    course = (
        db.query(Course)
        .filter(Course.id == payload.course_id, Course.workspace_id == ctx.workspace_id)
        .first()
    )
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "课程不存在")
    assignment = Assignment(workspace_id=ctx.workspace_id, **payload.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/courses/{course_id}/assignments", response_model=list[AssignmentOut])
def list_assignments(
    course_id: str,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    return (
        db.query(Assignment)
        .filter(Assignment.course_id == course_id, Assignment.workspace_id == ctx.workspace_id)
        .order_by(Assignment.created_at.desc())
        .all()
    )


@router.get("/assignments/{assignment_id}/stats", response_model=AssignmentStatsOut)
def assignment_stats(
    assignment_id: str,
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

    submissions = (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment_id, Submission.workspace_id == ctx.workspace_id)
        .all()
    )

    scores: list[float] = []
    # rubric_item_id -> {"name", "max_score", "scores"}
    item_agg: dict[str, dict] = {}

    for sub in submissions:
        for version in sub.versions:
            review = (
                db.query(Review)
                .filter(Review.submission_version_id == version.id, Review.status == "published")
                .first()
            )
            if review is None or review.publish is None:
                continue
            scores.append(review.publish.score)
            for item in review.items:
                decision = item.decision
                if decision is None or decision.final_band_id is None:
                    continue
                band = db.get(RubricBand, decision.final_band_id)
                rubric_item = db.get(RubricItem, item.rubric_item_id)
                if band is None or rubric_item is None:
                    continue
                agg = item_agg.setdefault(
                    rubric_item.id,
                    {"name": rubric_item.name, "max_score": rubric_item.max_score, "scores": []},
                )
                agg["scores"].append(band.score)

    item_avg = [
        ItemAvg(
            rubric_item_name=a["name"],
            avg_score=round(sum(a["scores"]) / len(a["scores"]), 1),
            max_score=a["max_score"],
        )
        for a in item_agg.values()
    ]

    return AssignmentStatsOut(
        assignment_id=assignment_id,
        published_count=len(scores),
        avg_score=round(sum(scores) / len(scores), 1) if scores else None,
        max_score=max(scores) if scores else None,
        min_score=min(scores) if scores else None,
        scores=scores,
        item_avg=item_avg,
    )
