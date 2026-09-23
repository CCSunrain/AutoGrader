"""Auth endpoints: register, login, me."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.roles import Role
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Membership, User, Workspace
from app.schemas.auth import (
    LoginRequest,
    MeOut,
    RegisterRequest,
    TokenResponse,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_token(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    if db.query(User).filter(User.email == payload.email).first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "该邮箱已注册")

    user = User(
        email=payload.email,
        username=payload.username,
        password_hash=hash_password(payload.password),
        is_demo=payload.is_demo,
        account_type=payload.account_type if payload.account_type in ("teacher", "student") else "teacher",
    )
    db.add(user)
    db.flush()  # populate user.id

    # every new user gets an isolated workspace where they are the owner
    workspace = Workspace(
        name=f"{user.username} 的工作区",
        slug=f"ws-{user.id[:8]}",
        created_by=user.id,
    )
    db.add(workspace)
    db.flush()
    db.add(Membership(workspace_id=workspace.id, user_id=user.id, role=Role.OWNER.value))
    db.commit()
    db.refresh(user)
    return _issue_token(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "邮箱或密码错误")
    if not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号已停用")
    return _issue_token(user)


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user)) -> MeOut:
    return MeOut.model_validate(user)
