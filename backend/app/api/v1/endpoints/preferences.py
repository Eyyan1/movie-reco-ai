from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.preference import (
    RecommendationFeedbackRequest,
    UserPreferenceResponse,
    UserPreferenceUpdate,
)
from app.services.preference_service import PreferenceService

router = APIRouter()


@router.get("/me", response_model=UserPreferenceResponse)
def get_preferences(current_user: User = Depends(require_current_user), db: Session = Depends(get_db)) -> UserPreferenceResponse:
    service = PreferenceService(db)
    return service.get_preferences_response(current_user.id)


@router.put("/me", response_model=UserPreferenceResponse)
def update_preferences(
    payload: UserPreferenceUpdate,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> UserPreferenceResponse:
    service = PreferenceService(db)
    return service.update_preferences(current_user.id, payload)


@router.post("/feedback", response_model=UserPreferenceResponse)
def save_feedback(
    payload: RecommendationFeedbackRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> UserPreferenceResponse:
    service = PreferenceService(db)
    return service.apply_feedback(current_user.id, payload)
