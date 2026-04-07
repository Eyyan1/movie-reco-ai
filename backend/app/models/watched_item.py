from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WatchedItem(Base):
    __tablename__ = "watched_items"
    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uq_watched_user_movie"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    movie_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    genre: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    runtime: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rating: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tagline: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    poster_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    backdrop_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    watched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
