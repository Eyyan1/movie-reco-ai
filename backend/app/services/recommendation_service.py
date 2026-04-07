from sqlalchemy.orm import Session

from app.schemas.preference import UserPreferenceResponse
from app.schemas.recommendation import RecommendationResponse
from app.services.preference_service import PreferenceService
from app.services.tmdb_service import TMDBService


class RecommendationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.preference_service = PreferenceService(db)
        self.tmdb_service = TMDBService()

    def get_recommendations(
        self,
        prompt: str,
        user_id: str | None = None,
    ) -> RecommendationResponse:
        preferences: UserPreferenceResponse | None = (
            self.preference_service.get_preferences_payload(user_id)
            if user_id
            else None
        )
        return self.tmdb_service.get_recommendations(prompt, preferences)
