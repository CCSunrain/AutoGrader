"""Rubric endpoints with nested items/bands and version freezing."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.core.deps import AuthContext, get_auth_context, require_roles
from app.core.roles import Role
from app.models import Rubric, RubricBand, RubricItem, RubricVersion
from app.schemas.rubric import RubricCreate, RubricOut

router = APIRouter(prefix="/rubrics", tags=["rubrics"])

_MANAGE = require_roles(Role.OWNER, Role.TEACHER)


def _load_rubric(db: Session, rubric_id: str) -> Rubric:
    rubric = (
        db.query(Rubric)
        .options(
            selectinload(Rubric.versions)
            .selectinload(RubricVersion.items)
            .selectinload(RubricItem.bands)
        )
        .filter(Rubric.id == rubric_id)
        .first()
    )
    if rubric is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "量表不存在")
    return rubric


@router.get("", response_model=list[RubricOut])
def list_rubrics(
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    return (
        db.query(Rubric)
        .options(
            selectinload(Rubric.versions)
            .selectinload(RubricVersion.items)
            .selectinload(RubricItem.bands)
        )
        .filter(Rubric.workspace_id == ctx.workspace_id)
        .order_by(Rubric.created_at.desc())
        .all()
    )


@router.post("", response_model=RubricOut, status_code=status.HTTP_201_CREATED)
def create_rubric(
    payload: RubricCreate,
    ctx: AuthContext = Depends(_MANAGE),
    db: Session = Depends(get_db),
):
    rubric = Rubric(
        workspace_id=ctx.workspace_id,
        title=payload.title,
        description=payload.description,
    )
    db.add(rubric)
    db.flush()

    version = RubricVersion(workspace_id=ctx.workspace_id, rubric_id=rubric.id, version_no=1)
    db.add(version)
    db.flush()

    for item in payload.items:
        row = RubricItem(
            workspace_id=ctx.workspace_id,
            rubric_version_id=version.id,
            name=item.name,
            description=item.description,
            max_score=item.max_score,
            order_index=item.order_index,
        )
        db.add(row)
        db.flush()
        for band in item.bands:
            db.add(
                RubricBand(
                    workspace_id=ctx.workspace_id,
                    rubric_item_id=row.id,
                    level=band.level,
                    score=band.score,
                    description=band.description,
                    order_index=band.order_index,
                )
            )

    db.commit()
    return _load_rubric(db, rubric.id)


@router.get("/{rubric_id}", response_model=RubricOut)
def get_rubric(
    rubric_id: str,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    rubric = _load_rubric(db, rubric_id)
    if rubric.workspace_id != ctx.workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "量表不存在")
    return rubric


@router.post("/{rubric_id}/versions/{version_id}/freeze", response_model=RubricOut)
def freeze_version(
    rubric_id: str,
    version_id: str,
    ctx: AuthContext = Depends(_MANAGE),
    db: Session = Depends(get_db),
):
    version = (
        db.query(RubricVersion)
        .filter(
            RubricVersion.id == version_id,
            RubricVersion.rubric_id == rubric_id,
            RubricVersion.workspace_id == ctx.workspace_id,
        )
        .first()
    )
    if version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "量表版本不存在")
    if version.frozen_at is None:
        version.frozen_at = datetime.now(timezone.utc)
        db.commit()
    return _load_rubric(db, rubric_id)
