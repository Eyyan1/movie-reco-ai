from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    prompt: str = Field(..., min_length=3, examples=["Stylish sci-fi with emotional depth"])
    user_id: str | None = Field(default=None, min_length=1)


class MovieRecommendation(BaseModel):
    id: int
    title: str
    year: int
    genre: str
    runtime: str | None
    rating: float
    tagline: str
    reason: str
    poster_url: str
    backdrop_url: str


class RecommendationGroup(BaseModel):
    group_title: str
    description: str
    movies: list[MovieRecommendation]


class RecommendationResponse(BaseModel):
    summary: str
    groups: list[RecommendationGroup]
