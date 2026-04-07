from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


QueryType = Literal[
    "general",
    "genre",
    "mood",
    "year",
    "person",
    "title_similarity",
    "narrative",
    "animation",
    "anime",
    "mixed_constraints",
]

IntentFamily = Literal[
    "romance",
    "sad_emotional",
    "feel_good",
    "funny",
    "dark_intense",
    "reference",
    "narrative",
    "use_case",
    "constraint",
    "mixed",
    "general",
]


class MovieIntent(BaseModel):
    query_type: QueryType = "general"
    intent_family: IntentFamily = "general"
    reference_titles: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    subgenres: list[str] = Field(default_factory=list)
    tone: list[str] = Field(default_factory=list)
    moods: list[str] = Field(default_factory=list)
    emotional_targets: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    narrative_targets: list[str] = Field(default_factory=list)
    story_outcomes: list[str] = Field(default_factory=list)
    ending_type: str | None = None
    character_dynamics: list[str] = Field(default_factory=list)
    setting: list[str] = Field(default_factory=list)
    scale: str | None = None
    pacing: str | None = None
    complexity: str | None = None
    violence_level: str | None = None
    audience: str | None = None
    year: int | None = None
    release_preference: str | None = None
    person: str | None = None
    language: str | None = None
    animation: bool = False
    anime: bool = False
    must_have: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    exclude_terms: list[str] = Field(default_factory=list)
    avoid_genres: list[str] = Field(default_factory=list)
    avoid_elements: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize(self) -> "MovieIntent":
        for field_name in [
            "reference_titles",
            "genres",
            "subgenres",
            "tone",
            "moods",
            "emotional_targets",
            "themes",
            "narrative_targets",
            "story_outcomes",
            "character_dynamics",
            "setting",
            "must_have",
            "nice_to_have",
            "exclude_terms",
            "avoid_genres",
            "avoid_elements",
        ]:
            value = getattr(self, field_name)
            setattr(self, field_name, _normalize_list(value))

        for field_name in [
            "intent_family",
            "ending_type",
            "scale",
            "pacing",
            "complexity",
            "violence_level",
            "audience",
            "release_preference",
            "person",
            "language",
        ]:
            value = getattr(self, field_name)
            if isinstance(value, str):
                cleaned = value.strip()
                setattr(self, field_name, cleaned or None)
        return self


def _normalize_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    seen: set[str] = set()
    normalized: list[str] = []
    for value in values:
        item = str(value).strip()
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(item)
    return normalized
