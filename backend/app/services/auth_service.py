from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.session import SessionToken
from app.models.user import User
from app.schemas.auth import LoginRequest, SignUpRequest, UserResponse


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def sign_up(self, payload: SignUpRequest) -> tuple[UserResponse, str]:
        email = payload.email.lower().strip()
        existing = self.db.query(User).filter(User.email == email).first()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with that email already exists.",
            )

        user = User(email=email, password_hash=self._hash_password(payload.password))
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        token = self._create_session(user.id)
        return self._to_user_response(user), token

    def login(self, payload: LoginRequest) -> tuple[UserResponse, str]:
        email = payload.email.lower().strip()
        user = self.db.query(User).filter(User.email == email).first()
        if user is None or not self._verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        token = self._create_session(user.id)
        return self._to_user_response(user), token

    def logout(self, raw_token: str | None) -> None:
        if not raw_token:
            return
        token_hash = self._hash_session_token(raw_token)
        session = self.db.get(SessionToken, token_hash)
        if session is not None:
            self.db.delete(session)
            self.db.commit()

    def get_user_from_session(self, raw_token: str | None) -> User | None:
        if not raw_token:
            return None
        token_hash = self._hash_session_token(raw_token)
        session = self.db.get(SessionToken, token_hash)
        if session is None:
            return None
        if session.expires_at <= datetime.now(timezone.utc):
            self.db.delete(session)
            self.db.commit()
            return None
        return self.db.get(User, session.user_id)

    def require_user(self, raw_token: str | None) -> User:
        user = self.get_user_from_session(raw_token)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.",
            )
        return user

    def _create_session(self, user_id: str) -> str:
        raw_token = secrets.token_urlsafe(32)
        token_hash = self._hash_session_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.auth_session_hours)
        session = SessionToken(id=token_hash, user_id=user_id, expires_at=expires_at)
        self.db.add(session)
        self.db.commit()
        return raw_token

    @staticmethod
    def _to_user_response(user: User) -> UserResponse:
        return UserResponse(id=user.id, email=user.email)

    @staticmethod
    def _hash_password(password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return f"{salt.hex()}:{digest.hex()}"

    @staticmethod
    def _verify_password(password: str, stored_hash: str) -> bool:
        try:
            salt_hex, digest_hex = stored_hash.split(":", maxsplit=1)
        except ValueError:
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return hmac.compare_digest(candidate, expected)

    @staticmethod
    def _hash_session_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
