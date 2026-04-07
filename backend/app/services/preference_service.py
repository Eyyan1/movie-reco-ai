from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.user_preference import UserPreference
from app.schemas.preference import (
    RecommendationFeedbackRequest,
    UserPreferenceResponse,
    UserPreferenceUpdate,
)


class PreferenceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create_preferences(self, user_id: str) -> UserPreference:
        preference = self.db.get(UserPreference, user_id)
        if preference is None:
            preference = UserPreference(user_id=user_id)
            self.db.add(preference)
            self.db.commit()
            self.db.refresh(preference)
        return preference

    def get_preferences(self, user_id: str) -> UserPreference | None:
        return self.db.get(UserPreference, user_id)

    def get_preferences_response(self, user_id: str) -> UserPreferenceResponse:
        preference = self.get_or_create_preferences(user_id)
        return self._to_response(preference)

    def get_preferences_payload(self, user_id: str) -> UserPreferenceResponse | None:
        preference = self.get_preferences(user_id)
        if preference is None:
            return None
        return self._to_response(preference)

    def update_preferences(
        self,
        user_id: str,
        payload: UserPreferenceUpdate,
    ) -> UserPreferenceResponse:
        preference = self.get_or_create_preferences(user_id)
        for field_name, value in payload.model_dump().items():
            setattr(preference, field_name, self._normalize_list(value) if isinstance(value, list) else value)
        self.db.add(preference)
        self.db.commit()
        self.db.refresh(preference)
        return self._to_response(preference)

    def apply_feedback(
        self,
        user_id: str,
        payload: RecommendationFeedbackRequest,
    ) -> UserPreferenceResponse:
        preference = self.get_or_create_preferences(user_id)
        genre_tokens = self._genre_tokens(payload.movie_genre)
        title = payload.movie_title.strip()

        if payload.sentiment == "up":
            preference.favorite_movies = self._merge_items(preference.favorite_movies, [title])
            preference.disliked_movies = self._remove_items(preference.disliked_movies, [title])
            if genre_tokens:
                preference.favorite_genres = self._merge_items(preference.favorite_genres, genre_tokens[:2])
                preference.disliked_genres = self._remove_items(preference.disliked_genres, genre_tokens)
        else:
            preference.disliked_movies = self._merge_items(preference.disliked_movies, [title])
            preference.favorite_movies = self._remove_items(preference.favorite_movies, [title])
            if genre_tokens:
                preference.disliked_genres = self._merge_items(preference.disliked_genres, genre_tokens[:2])
                preference.favorite_genres = self._remove_items(preference.favorite_genres, genre_tokens)

        self.db.add(preference)
        self.db.commit()
        self.db.refresh(preference)
        return self._to_response(preference)

    def _to_response(self, preference: UserPreference) -> UserPreferenceResponse:
        return UserPreferenceResponse(
            user_id=preference.user_id,
            favorite_genres=self._normalize_list(preference.favorite_genres),
            disliked_genres=self._normalize_list(preference.disliked_genres),
            favorite_movies=self._normalize_list(preference.favorite_movies),
            disliked_movies=self._normalize_list(preference.disliked_movies),
            preferred_decades=self._normalize_list(preference.preferred_decades),
            vibe_preferences=self._normalize_list(preference.vibe_preferences),
            avoid_gore=bool(preference.avoid_gore),
            avoid_sad_endings=bool(preference.avoid_sad_endings),
            complexity_preference=preference.complexity_preference,
        )

    @staticmethod
    def _normalize_list(values: list[str] | None) -> list[str]:
        if not values:
            return []
        seen: set[str] = set()
        normalized: list[str] = []
        for value in values:
            item = str(value).strip()
            if not item:
                continue
            dedupe_key = item.lower()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            normalized.append(item)
        return normalized

    def _merge_items(self, existing: list[str] | None, additions: list[str]) -> list[str]:
        return self._normalize_list([*(existing or []), *additions])

    def _remove_items(self, existing: list[str] | None, removals: list[str]) -> list[str]:
        removal_keys = {item.lower() for item in removals if item.strip()}
        return [item for item in self._normalize_list(existing) if item.lower() not in removal_keys]

    @staticmethod
    def _genre_tokens(genre_text: str) -> list[str]:
        return [
            token.strip()
            for token in genre_text.replace("/", ",").split(",")
            if token.strip()
        ]
