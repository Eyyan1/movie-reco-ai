from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    favorite_genres: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    disliked_genres: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    favorite_movies: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    disliked_movies: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_decades: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    vibe_preferences: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    avoid_gore: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    avoid_sad_endings: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    complexity_preference: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
