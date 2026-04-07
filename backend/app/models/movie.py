from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    genre: Mapped[str] = mapped_column(String(100), nullable=False)
    runtime: Mapped[str] = mapped_column(String(32), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    tagline: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    poster_gradient: Mapped[str] = mapped_column(String(255), nullable=False)

