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


def _write_items(db: Session, version: RubricVersion, items: list) -> None:
    """Write rubric items + bands into the given version."""
    for item in items:
        row = RubricItem(
            workspace_id=version.workspace_id,
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
                    workspace_id=version.workspace_id,
                    rubric_item_id=row.id,
                    level=band.level,
                    score=band.score,
                    description=band.description,
                    order_index=band.order_index,
                )
            )


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

    _write_items(db, version, payload.items)

    db.commit()
    return _load_rubric(db, rubric.id)


@router.put("/{rubric_id}", response_model=RubricOut)
def update_rubric(
    rubric_id: str,
    payload: RubricCreate,
    ctx: AuthContext = Depends(_MANAGE),
    db: Session = Depends(get_db),
):
    rubric = _load_rubric(db, rubric_id)
    if rubric.workspace_id != ctx.workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "量表不存在")

    latest = rubric.versions[-1] if rubric.versions else None

    if latest is not None and latest.frozen_at is None:
        # 编辑未冻结的最新版本：覆盖其 items/bands
        version = latest
        for item in list(version.items):
            db.delete(item)  # cascade 删除 bands
        version.items = []  # 清空 relationship 缓存
        db.flush()
    else:
        # 已冻结或不存在版本：创建新版本
        version = RubricVersion(
            workspace_id=ctx.workspace_id,
            rubric_id=rubric.id,
            version_no=len(rubric.versions) + 1,
        )
        db.add(version)
        db.flush()

    _write_items(db, version, payload.items)
    rubric.title = payload.title
    rubric.description = payload.description
    db.commit()
    db.expire_all()  # 清除 identity map 缓存，强制重新加载 versions/items
    return _load_rubric(db, rubric.id)


@router.delete("/{rubric_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rubric(
    rubric_id: str,
    ctx: AuthContext = Depends(_MANAGE),
    db: Session = Depends(get_db),
):
    rubric = _load_rubric(db, rubric_id)
    if rubric.workspace_id != ctx.workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "量表不存在")
    db.delete(rubric)  # cascade 删除 versions/items/bands
    db.commit()


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
