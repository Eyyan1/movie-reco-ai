from __future__ import annotations

from pydantic import BaseModel

from app.schemas.recommendation import MovieRecommendation


class LibraryItemCreate(MovieRecommendation):
    pass


class WatchlistResponse(BaseModel):
    items: list[MovieRecommendation]


class WatchedHistoryResponse(BaseModel):
    items: list[MovieRecommendation]
