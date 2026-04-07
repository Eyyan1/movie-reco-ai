from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, SignUpRequest, UserResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/signup", response_model=AuthResponse)
def sign_up(payload: SignUpRequest, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    service = AuthService(db)
    user, token = service.sign_up(payload)
    _set_auth_cookie(response, token)
    return AuthResponse(user=user)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    service = AuthService(db)
    user, token = service.login(payload)
    _set_auth_cookie(response, token)
    return AuthResponse(user=user)


@router.post("/logout")
def logout(
    response: Response,
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
    current_user: User | None = Depends(get_current_user),
) -> dict[str, str]:
    service = AuthService(db)
    service.logout(session_token)
    response.delete_cookie(
        settings.auth_cookie_name,
        path="/",
        domain=settings.auth_cookie_domain,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
    )
    return {"status": "ok"}


@router.get("/me", response_model=UserResponse | None)
def get_current_account(current_user: User | None = Depends(get_current_user)) -> UserResponse | None:
    if current_user is None:
        return None
    return UserResponse(id=current_user.id, email=current_user.email)


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        samesite=settings.auth_cookie_samesite,
        secure=settings.auth_cookie_secure,
        max_age=settings.auth_session_hours * 3600,
        path="/",
        domain=settings.auth_cookie_domain,
    )
