from __future__ import annotations

from pydantic import BaseModel, Field


class UserPreferenceBase(BaseModel):
    favorite_genres: list[str] = Field(default_factory=list)
    disliked_genres: list[str] = Field(default_factory=list)
    favorite_movies: list[str] = Field(default_factory=list)
    disliked_movies: list[str] = Field(default_factory=list)
    preferred_decades: list[str] = Field(default_factory=list)
    vibe_preferences: list[str] = Field(default_factory=list)
    avoid_gore: bool = False
    avoid_sad_endings: bool = False
    complexity_preference: str | None = None


class UserPreferenceUpdate(UserPreferenceBase):
    pass


class UserPreferenceResponse(UserPreferenceBase):
    user_id: str


class RecommendationFeedbackRequest(BaseModel):
    movie_id: int
    movie_title: str
    movie_genre: str = ""
    sentiment: str = Field(pattern="^(up|down)$")
