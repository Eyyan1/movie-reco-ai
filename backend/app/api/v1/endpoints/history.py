from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.library import LibraryItemCreate, WatchedHistoryResponse
from app.services.library_service import LibraryService

router = APIRouter()


@router.get("", response_model=WatchedHistoryResponse)
def list_history(current_user: User = Depends(require_current_user), db: Session = Depends(get_db)) -> WatchedHistoryResponse:
    service = LibraryService(db)
    return service.list_watched(current_user.id)


@router.post("", response_model=WatchedHistoryResponse)
def mark_watched(
    payload: LibraryItemCreate,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> WatchedHistoryResponse:
    service = LibraryService(db)
    return service.mark_watched(current_user.id, payload)
