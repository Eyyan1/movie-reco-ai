from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter()


@router.post("", response_model=RecommendationResponse)
def create_recommendations(
    payload: RecommendationRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
) -> RecommendationResponse:
    service = RecommendationService(db)
    effective_user_id = current_user.id if current_user is not None else payload.user_id
    return service.get_recommendations(payload.prompt, effective_user_id)
