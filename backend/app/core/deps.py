"""FastAPI dependencies: current user, workspace resolution, role enforcement."""
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.roles import Role
from app.core.security import decode_access_token
from app.models import Membership, User


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the Authorization bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未认证：缺少 Bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "无效或过期的 token")
    user = db.get(User, payload.get("sub"))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在或已停用")
    return user


def get_current_workspace(
    x_workspace_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> str:
    """Resolve the active workspace id for the request.

    Prefers the `X-Workspace-Id` header; falls back to the user's earliest
    membership. Multi-tenant isolation relies on every business query being
    filtered by this workspace id.
    """
    if x_workspace_id:
        membership = (
            db.query(Membership)
            .filter(Membership.workspace_id == x_workspace_id, Membership.user_id == user.id)
            .first()
        )
        if membership is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "你不是该工作区成员")
        return x_workspace_id
    membership = (
        db.query(Membership)
        .filter(Membership.user_id == user.id)
        .order_by(Membership.created_at.asc())
        .first()
    )
    if membership is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "你尚未加入任何工作区")
    return membership.workspace_id


@dataclass
class AuthContext:
    """Authenticated request context: user + active workspace + role."""

    user: User
    workspace_id: str
    role: Role | None


def get_auth_context(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace),
) -> AuthContext:
    membership = (
        db.query(Membership)
        .filter(Membership.workspace_id == workspace_id, Membership.user_id == user.id)
        .first()
    )
    role = Role(membership.role) if membership else None
    return AuthContext(user=user, workspace_id=workspace_id, role=role)


def require_roles(*roles: Role):
    """Dependency factory enforcing that the caller holds one of `roles`."""

    def dep(ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if ctx.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "权限不足")
        return ctx

    return dep
