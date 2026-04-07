from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.watched_item import WatchedItem
from app.models.watchlist_item import WatchlistItem
from app.schemas.library import LibraryItemCreate, WatchedHistoryResponse, WatchlistResponse
from app.schemas.recommendation import MovieRecommendation


class LibraryService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_to_watchlist(self, user_id: str, payload: LibraryItemCreate) -> WatchlistResponse:
        item = (
            self.db.query(WatchlistItem)
            .filter(WatchlistItem.user_id == user_id, WatchlistItem.movie_id == payload.id)
            .first()
        )
        if item is None:
            item = WatchlistItem(user_id=user_id, movie_id=payload.id, **self._movie_payload(payload))
            self.db.add(item)
            self.db.commit()
        return self.list_watchlist(user_id)

    def remove_from_watchlist(self, user_id: str, movie_id: int) -> WatchlistResponse:
        item = (
            self.db.query(WatchlistItem)
            .filter(WatchlistItem.user_id == user_id, WatchlistItem.movie_id == movie_id)
            .first()
        )
        if item is not None:
            self.db.delete(item)
            self.db.commit()
        return self.list_watchlist(user_id)

    def list_watchlist(self, user_id: str) -> WatchlistResponse:
        items = (
            self.db.query(WatchlistItem)
            .filter(WatchlistItem.user_id == user_id)
            .order_by(WatchlistItem.created_at.desc())
            .all()
        )
        return WatchlistResponse(items=[self._to_movie(item) for item in items])

    def mark_watched(self, user_id: str, payload: LibraryItemCreate) -> WatchedHistoryResponse:
        item = (
            self.db.query(WatchedItem)
            .filter(WatchedItem.user_id == user_id, WatchedItem.movie_id == payload.id)
            .first()
        )
        if item is None:
            item = WatchedItem(user_id=user_id, movie_id=payload.id, **self._movie_payload(payload))
            self.db.add(item)
        watchlist_item = (
            self.db.query(WatchlistItem)
            .filter(WatchlistItem.user_id == user_id, WatchlistItem.movie_id == payload.id)
            .first()
        )
        if watchlist_item is not None:
            self.db.delete(watchlist_item)
        self.db.commit()
        return self.list_watched(user_id)

    def list_watched(self, user_id: str) -> WatchedHistoryResponse:
        items = (
            self.db.query(WatchedItem)
            .filter(WatchedItem.user_id == user_id)
            .order_by(WatchedItem.watched_at.desc())
            .all()
        )
        return WatchedHistoryResponse(items=[self._to_movie(item) for item in items])

    @staticmethod
    def _movie_payload(payload: LibraryItemCreate) -> dict:
        return {
            "title": payload.title,
            "year": payload.year,
            "genre": payload.genre,
            "runtime": payload.runtime,
            "rating": payload.rating,
            "tagline": payload.tagline,
            "reason": payload.reason,
            "poster_url": payload.poster_url,
            "backdrop_url": payload.backdrop_url,
        }

    @staticmethod
    def _to_movie(item: WatchlistItem | WatchedItem) -> MovieRecommendation:
        return MovieRecommendation(
            id=item.movie_id,
            title=item.title,
            year=item.year,
            genre=item.genre,
            runtime=item.runtime,
            rating=item.rating,
            tagline=item.tagline,
            reason=item.reason,
            poster_url=item.poster_url,
            backdrop_url=item.backdrop_url,
        )
