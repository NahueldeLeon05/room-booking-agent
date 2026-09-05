from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import create_access_token, verify_password
from app.api.deps import get_current_user
from app.infrastructure.database import get_session
from app.infrastructure.models import UserModel


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class CurrentUserResponse(BaseModel):
    id: int
    username: str


@router.post("/login", response_model=TokenResponse)
def login(
    credentials: LoginRequest,
    session: Annotated[Session, Depends(get_session)],
) -> TokenResponse:
    user = session.scalar(
        select(UserModel).where(UserModel.username == credentials.username)
    )

    if user is None or not verify_password(
        credentials.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        token_type="bearer",
    )


@router.get("/me", response_model=CurrentUserResponse)
def current_user(
    user: Annotated[UserModel, Depends(get_current_user)],
) -> CurrentUserResponse:
    return CurrentUserResponse(id=user.id, username=user.username)
