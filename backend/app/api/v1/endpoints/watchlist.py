from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.library import LibraryItemCreate, WatchlistResponse
from app.services.library_service import LibraryService

router = APIRouter()


@router.get("", response_model=WatchlistResponse)
def list_watchlist(current_user: User = Depends(require_current_user), db: Session = Depends(get_db)) -> WatchlistResponse:
    service = LibraryService(db)
    return service.list_watchlist(current_user.id)


@router.post("", response_model=WatchlistResponse)
def add_to_watchlist(
    payload: LibraryItemCreate,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> WatchlistResponse:
    service = LibraryService(db)
    return service.add_to_watchlist(current_user.id, payload)


@router.delete("/{movie_id}", response_model=WatchlistResponse)
def remove_from_watchlist(
    movie_id: int,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> WatchlistResponse:
    service = LibraryService(db)
    return service.remove_from_watchlist(current_user.id, movie_id)
