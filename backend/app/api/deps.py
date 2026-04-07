from __future__ import annotations

from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService


def get_current_user(
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> User | None:
    service = AuthService(db)
    return service.get_user_from_session(session_token)


def require_current_user(
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> User:
    service = AuthService(db)
    return service.require_user(session_token)
