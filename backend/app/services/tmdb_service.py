from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
import logging
import math
import re
import time

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.intent import MovieIntent
from app.schemas.preference import UserPreferenceResponse
from app.schemas.recommendation import (
    MovieRecommendation,
    RecommendationGroup,
    RecommendationResponse,
)
from app.services.embedding_service import EmbeddingService
from app.services.intent_parser import IntentParserService

GENRE_MAP = {
    "animation": {"id": 16, "label": "Animation", "title": "Animated Picks"},
    "cartoon": {"id": 16, "label": "Animation", "title": "Animated Picks"},
    "comedy": {"id": 35, "label": "Comedy", "title": "Comedy picks"},
    "drama": {"id": 18, "label": "Drama", "title": "Drama essentials"},
    "family": {"id": 10751, "label": "Family", "title": "Family-friendly nights"},
    "horror": {"id": 27, "label": "Horror", "title": "Horror nights"},
    "romance": {"id": 10749, "label": "Romance", "title": "Romance picks"},
    "sci-fi": {"id": 878, "label": "Sci-Fi", "title": "Sci-fi futures"},
    "science fiction": {"id": 878, "label": "Sci-Fi", "title": "Sci-fi futures"},
    "thriller": {"id": 53, "label": "Thriller", "title": "Thriller tension"},
}

SOFT_PREFERENCE_MAP = {
    "sad": "sad",
    "heartbreaking": "heartbreaking",
    "stylish": "stylish",
    "dark": "dark",
    "darker": "darker",
    "emotional": "emotional",
    "cry-worthy": "cry-worthy",
    "cry worthy": "cry-worthy",
    "cathartic": "cathartic",
    "depressing": "depressing",
    "funny": "funny",
    "fun movie": "fun",
    "entertaining": "fun",
    "comedy movie": "funny",
    "laugh-out-loud": "laugh-out-loud",
    "laugh out loud": "laugh-out-loud",
    "witty": "witty",
    "banter": "banter",
    "rom com": "rom-com",
    "rom-com": "rom-com",
    "romantic comedy": "rom-com",
    "cozy": "cozy",
    "tragic": "tragic",
    "warmer": "warmer",
    "less dark": "less-dark",
    "less confusing": "less-confusing",
    "lighter": "lighter",
    "more hopeful": "more-hopeful",
    "more emotional": "more-emotional",
    "funnier": "funnier",
    "mind-bending": "mind-bending",
    "mind bending": "mind-bending",
    "comfort": "comfort",
    "comfort movie": "comfort",
    "wholesome": "wholesome",
    "relaxing": "relaxing",
    "relaxed night": "relaxing",
    "easy watch": "easy-watch",
    "healing": "healing",
    "emotionally healing": "healing",
    "movie with heart": "healing",
    "with heart": "healing",
    "heartfelt movie": "healing",
    "heartfelt": "healing",
    "family drama": "family-drama",
    "heartbreaking romance": "heartbreaking-romance",
    "relationship-centered": "relationship-centered",
}

TONE_KEYWORDS = {
    "warm": "warm",
    "warmer": "warm",
    "cozy": "cozy",
    "comfort": "comfort",
    "wholesome": "wholesome",
    "relaxing": "relaxing",
    "intense": "intense",
    "dark": "dark",
    "uplifting": "uplifting",
    "bittersweet": "bittersweet",
    "romantic": "romantic",
    "witty": "witty",
    "banter": "banter",
    "stylish": "stylish",
    "visually stunning": "visually stunning",
    "heartbreaking": "heartbreaking",
    "healing": "healing",
    "heartfelt": "healing",
    "with heart": "warm",
    "movie with heart": "warm",
    "cathartic": "cathartic",
    "cry-worthy": "cry-worthy",
    "family drama": "family drama",
    "heartbreaking romance": "heartbreaking romance",
    "relationship-centered": "relationship-centered drama",
}

EMOTIONAL_TARGET_KEYWORDS = {
    "sad": "sad",
    "emotional": "emotional",
    "emotional depth": "emotional",
    "heartbreaking": "heartbreaking",
    "bittersweet": "bittersweet",
    "warm": "warm",
    "warmer": "warm",
    "uplifting": "uplifting",
    "healing": "emotional healing",
    "emotionally healing": "emotional healing",
    "movie with heart": "warm",
    "with heart": "warm",
    "heartfelt movie": "emotional healing",
    "heartfelt": "emotional",
    "cathartic": "emotional healing",
    "cry-worthy": "sad",
    "family drama": "emotional",
    "heartbreaking romance": "heartbreaking",
    "warm but sad": "bittersweet",
    "relationship-centered drama": "emotional",
    "cozy": "cozy",
    "comfort": "comfort",
    "wholesome": "wholesome",
    "relaxing": "relaxing",
    "easy watch": "easy watch",
    "tragic": "tragic",
    "movie to cry to": "sad",
    "cry to": "sad",
    "tearjerker": "heartbreaking",
    "tear jerker": "heartbreaking",
    "emotional healing": "emotional healing",
}

THEME_KEYWORDS = {
    "revenge": "revenge",
    "sacrifice": "sacrifice",
    "survival": "survival",
    "love": "love",
    "family": "family",
    "heart": "love",
    "family conflict": "family conflict",
    "reconciliation": "reconciliation",
    "recovery": "recovery",
    "forgiveness": "forgiveness",
    "memory": "memory",
    "grief": "grief",
    "loss": "loss",
    "loneliness": "loneliness",
    "redemption": "redemption",
}

STORY_OUTCOME_KEYWORDS = {
    "villain wins": "villain wins",
    "tragic ending": "tragic ending",
    "happy ending": "happy ending",
    "bittersweet ending": "bittersweet ending",
    "twist ending": "twist ending",
    "underdog": "underdog story",
    "redemption arc": "redemption arc",
    "survival story": "survival story",
    "emotional healing": "emotional healing",
}

NARRATIVE_TARGET_KEYWORDS = {
    "villain wins": "villain wins",
    "happy ending": "happy ending",
    "tragic ending": "tragic ending",
    "bittersweet ending": "bittersweet ending",
    "revenge": "revenge",
    "sacrifice": "sacrifice",
    "redemption": "redemption",
    "redemption arc": "redemption",
    "twist ending": "twist ending",
    "underdog": "underdog story",
    "underdog story": "underdog story",
    "emotional healing": "emotional healing",
}

CHARACTER_DYNAMIC_KEYWORDS = {
    "ensemble": "ensemble cast",
    "ensemble cast": "ensemble cast",
    "antihero": "antihero",
    "strong female lead": "strong female lead",
    "powerful villain": "powerful villain",
    "mentor": "mentor-student",
    "enemies to lovers": "enemies to lovers",
    "father-daughter": "father-daughter",
    "mother": "mother-child",
    "father": "father-child",
    "daughter": "parent-child",
    "son": "parent-child",
    "relationship": "relationship-centered",
    "found family": "found family",
}

FORMAL_QUALITY_KEYWORDS = {
    "slow burn": ("pacing", "slow burn"),
    "fast paced": ("pacing", "fast paced"),
    "fast-paced": ("pacing", "fast paced"),
    "dialogue-heavy": ("pacing", "dialogue-heavy"),
    "action-heavy": ("pacing", "action-heavy"),
    "easy watch": ("complexity", "easy watch"),
    "less confusing": ("complexity", "less confusing"),
    "cerebral": ("complexity", "cerebral"),
}

SETTING_KEYWORDS = {
    "space": "space",
    "small town": "small town",
    "post-apocalyptic": "post-apocalyptic",
    "school": "school",
    "city": "city",
}

LANGUAGE_KEYWORDS = {
    "japanese": "Japanese",
    "korean": "Korean",
    "french": "French",
    "spanish": "Spanish",
    "english": "English",
}

AVOID_GENRE_KEYWORDS = {
    "no horror": "Horror",
    "not horror": "Horror",
    "no anime": "Animation",
}

AVOID_ELEMENT_KEYWORDS = {
    "no gore": "gore",
    "not too scary": "too scary",
    "no old movies": "old movies",
    "not too long": "long runtime",
    "family friendly": "family friendly",
}

TMDB_GENRE_NAMES = {
    12: "Adventure",
    14: "Fantasy",
    16: "Animation",
    18: "Drama",
    27: "Horror",
    28: "Action",
    35: "Comedy",
    36: "History",
    37: "Western",
    53: "Thriller",
    80: "Crime",
    87: "Science Fiction",
    99: "Documentary",
    9648: "Mystery",
    10402: "Music",
    10749: "Romance",
    10751: "Family",
    10752: "War",
    10770: "TV Movie",
    878: "Science Fiction",
}

MAX_GROUPS = 3
MAX_MOVIES_PER_GROUP = 6
MAX_CANDIDATES = 12
MAX_SIMILAR_CANDIDATES = 36
MAX_EMBEDDING_CANDIDATES = 30
DETAILS_ENRICH_COUNT = 3
CACHE_TTL_SECONDS = 600
FAMILY_PRIMARY_GENRES = {
    "sad_emotional": {18, 10749, 10751},
    "romance": {10749, 35, 18},
    "funny": {35, 10749, 12},
    "feel_good": {35, 10751, 10749},
    "dark_intense": {53, 18, 9648},
}
FAMILY_FILTER_RULES = {
    "sad_emotional": {"allow": {18, 10749, 10751}, "soft_allow": {36}, "block": {28, 878, 53, 27}},
    "romance": {"allow": {10749, 18, 35}, "soft_allow": {10751}, "block": {27, 80, 10752, 28}},
    "funny": {"allow": {35, 10749, 12}, "soft_allow": {10751, 18}, "block": {27, 53, 80, 10752, 28}},
    "feel_good": {"allow": {35, 10751, 10749, 12}, "soft_allow": {18}, "block": {27, 53, 80, 10752, 28}},
    "dark_intense": {"allow": {53, 18, 9648}, "soft_allow": {27}, "block": {10751, 35}},
    "narrative": {"allow": {18, 53, 9648}, "soft_allow": {878, 28}, "block": {35, 10751}},
}
EMOTIONAL_TEXT_SIGNALS = {"love", "grief", "loss", "memory", "identity", "family", "humanity"}
SAD_TEXT_SIGNALS = {"grief", "loss", "heartbreak", "love", "family", "memory", "tragedy", "loneliness"}
THOUGHTFUL_SCIFI_TEXT_SIGNALS = {"future", "space", "ai", "time", "alien", "mission", "isolation", "consciousness"}
SPECIAL_CONTENT_TERMS = {"concert", "special", "featurette", "behind the scenes", "making of", "compilation"}
GORE_SIGNALS = {"gore", "bloody", "slasher", "brutal", "massacre", "torture", "gruesome"}
SAD_ENDING_SIGNALS = {"tragic", "grief", "mourning", "loss", "heartbreak", "terminal", "death"}
EMOTION_SIGNAL_KEYWORDS = {
    "sad": {"grief", "loss", "heartbreak", "death", "mourning", "loneliness", "family", "memory", "tragedy", "terminal", "separation"},
    "emotional": {"grief", "loss", "heart", "family", "memory", "humanity", "connection", "love"},
    "heartbreaking": {"heartbreak", "tragic", "mourning", "loss", "terminal", "goodbye", "separation"},
    "bittersweet": {"bittersweet", "longing", "memory", "parting", "reunion", "goodbye"},
    "warm": {"hope", "healing", "connection", "friendship", "family", "kindness", "second chance", "reunion", "support", "joy"},
    "uplifting": {"hope", "healing", "friendship", "support", "joy", "kindness", "reunion", "inspiring"},
    "cry-worthy": {"grief", "heartbreak", "loss", "terminal", "separation", "sacrifice", "mourning"},
    "healing": {"healing", "recovery", "reunion", "second chance", "forgiveness", "reconciliation", "support"},
    "cathartic": {"grief", "recovery", "release", "forgiveness", "acceptance", "healing"},
    "cozy": {"warm", "comfort", "home", "family", "friendship", "kindness", "soft", "gentle"},
    "comfort": {"comfort", "healing", "support", "family", "friendship", "kindness", "home", "heartwarming"},
    "wholesome": {"kindness", "community", "support", "family", "friendship", "heartwarming", "joy"},
    "relaxing": {"gentle", "easy", "light", "warm", "comfort", "friendship"},
    "easy watch": {"easy", "light", "accessible", "gentle", "warm", "comfort"},
    "tragic": {"tragic", "doom", "loss", "death", "fall", "mourning", "sacrifice"},
    "emotional healing": {"healing", "recovery", "reunion", "support", "connection", "hope", "second chance"},
}
NARRATIVE_SIGNAL_KEYWORDS = {
    "villain wins": {"defeat", "doomed", "destruction", "collapse", "sacrifice", "no escape", "revenge", "corruption", "final loss", "fall", "darkness"},
    "tragic ending": {"tragic", "doom", "death", "loss", "mourning", "sacrifice", "final loss"},
    "bittersweet ending": {"bittersweet", "parting", "reunion", "memory", "loss", "hope"},
    "happy ending": {"hope", "joy", "reunion", "healing", "support", "second chance"},
    "revenge": {"revenge", "vengeance", "payback", "retaliation"},
    "sacrifice": {"sacrifice", "selfless", "giving up", "save others"},
    "redemption": {"redemption", "atonement", "forgiveness", "second chance"},
    "twist ending": {"twist", "secret", "reveal", "shocking", "unexpected"},
    "underdog story": {"underdog", "outsider", "against all odds", "unlikely", "comeback"},
    "emotional healing": {"healing", "recovery", "acceptance", "support", "reunion"},
}
ROMANCE_SIGNAL_KEYWORDS = {"love", "relationship", "marriage", "couple", "romance", "heartbreak", "affair", "reunion"}
HEALING_POSITIVE_SIGNALS = {
    "healing",
    "grief",
    "recovery",
    "reunion",
    "second chance",
    "family conflict",
    "reconciliation",
    "heartbreak",
    "terminal illness",
    "sacrifice",
    "memory",
    "forgiveness",
    "loss",
    "emotional journey",
    "mother",
    "father",
    "daughter",
    "son",
    "relationship",
}
HEALING_NEGATIVE_SIGNALS = {
    "superhero",
    "franchise",
    "explosive",
    "mission",
    "murder",
    "crime",
    "terror",
    "killer",
    "violent",
}
ABSTRACT_COMPLEXITY_SIGNALS = {"abstract", "nonlinear", "surreal", "dense", "labyrinth", "fractured", "metaphysical", "dream"}
BLOCKBUSTER_SPECTACLE_SIGNALS = {"superhero", "franchise", "explosive", "mission", "save the world", "blockbuster"}
FUNNY_POSITIVE_SIGNALS = {
    "funny",
    "hilarious",
    "awkward",
    "chaotic",
    "absurd",
    "ridiculous",
    "outrageous",
    "prank",
    "friendship",
    "wedding",
    "date",
    "mistaken identity",
    "banter",
    "charming",
    "misadventure",
    "laugh",
    "rivalry",
    "odd couple",
    "slacker",
    "party",
}
FUNNY_NEGATIVE_SIGNALS = {
    "murder",
    "revenge",
    "corruption",
    "trauma",
    "war",
    "terror",
    "killer",
    "brutality",
    "doomed",
    "grim",
    "bleak",
}
FEEL_GOOD_POSITIVE_SIGNALS = {
    "hope",
    "healing",
    "friendship",
    "family",
    "kindness",
    "joy",
    "reunion",
    "second chance",
    "support",
    "heartwarming",
    "uplifting",
    "community",
    "love",
    "comfort",
}
FEEL_GOOD_NEGATIVE_SIGNALS = {
    "revenge",
    "murder",
    "killer",
    "terror",
    "corruption",
    "doomed",
    "brutal",
    "violent",
    "collapse",
    "despair",
    "grim",
    "bleak",
}
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParsedPrompt:
    intent_family: str
    year: int | None
    hard_genres: list[dict]
    soft_preferences: list[str]
    tone: list[str]
    emotional_targets: list[str]
    themes: list[str]
    narrative_targets: list[str]
    story_outcomes: list[str]
    ending_type: str | None
    character_dynamics: list[str]
    setting: list[str]
    scale: str | None
    pacing: str | None
    complexity: str | None
    violence_level: str | None
    wants_anime: bool
    wants_animation: bool
    person_name: str | None
    reference_titles: list[str]
    subgenres: list[str]
    language: str | None
    must_have: list[str]
    nice_to_have: list[str]
    exclude_terms: list[str]
    avoid_genres: list[str]
    avoid_elements: list[str]
    release_preference: str | None
    audience: str | None
    query_type: str
    retrieval_summary: str


@dataclass(frozen=True)
class GroupPlan:
    key: str
    title: str
    description: str
    mode: str
    year: int | None = None
    genre_id: int | None = None
    query: str | None = None
    original_language: str | None = None
    sort_by: str = "popularity.desc"
    min_vote_count: int = 100
    max_vote_count: int | None = None
    person_id: int | None = None
    person_name: str | None = None
    reference_movie_id: int | None = None
    reference_movie_title: str | None = None


def parse_prompt(prompt: str) -> ParsedPrompt:
    normalized_prompt = prompt.lower()
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", normalized_prompt)
    year = int(year_match.group(1)) if year_match else None

    hard_genres: list[dict] = []
    seen_ids: set[int] = set()
    wants_animation = False
    wants_anime = "anime" in normalized_prompt

    for keyword, genre_config in GENRE_MAP.items():
        if keyword in normalized_prompt and genre_config["id"] not in seen_ids:
            hard_genres.append(genre_config)
            seen_ids.add(genre_config["id"])
        if keyword in {"animation", "cartoon"} and keyword in normalized_prompt:
            wants_animation = True

    if wants_anime and 16 not in seen_ids:
        hard_genres.append({"id": 16, "label": "Animation", "title": "Animated Picks"})

    soft_preferences = [
        mapped
        for keyword, mapped in SOFT_PREFERENCE_MAP.items()
        if keyword in normalized_prompt
    ]
    tone = [value for keyword, value in TONE_KEYWORDS.items() if keyword in normalized_prompt]
    emotional_targets = [
        value for keyword, value in EMOTIONAL_TARGET_KEYWORDS.items() if keyword in normalized_prompt
    ]
    themes = [value for keyword, value in THEME_KEYWORDS.items() if keyword in normalized_prompt]
    narrative_targets = [
        value for keyword, value in NARRATIVE_TARGET_KEYWORDS.items() if keyword in normalized_prompt
    ]
    story_outcomes = [
        value for keyword, value in STORY_OUTCOME_KEYWORDS.items() if keyword in normalized_prompt
    ]
    character_dynamics = [
        value
        for keyword, value in CHARACTER_DYNAMIC_KEYWORDS.items()
        if keyword in normalized_prompt
    ]
    setting = [value for keyword, value in SETTING_KEYWORDS.items() if keyword in normalized_prompt]
    language = next(
        (value for keyword, value in LANGUAGE_KEYWORDS.items() if keyword in normalized_prompt),
        None,
    )
    pacing = next(
        (
            value
            for keyword, (kind, value) in FORMAL_QUALITY_KEYWORDS.items()
            if kind == "pacing" and keyword in normalized_prompt
        ),
        None,
    )
    complexity = next(
        (
            value
            for keyword, (kind, value) in FORMAL_QUALITY_KEYWORDS.items()
            if kind == "complexity" and keyword in normalized_prompt
        ),
        None,
    )
    avoid_genres = [
        value for keyword, value in AVOID_GENRE_KEYWORDS.items() if keyword in normalized_prompt
    ]
    avoid_elements = [
        value for keyword, value in AVOID_ELEMENT_KEYWORDS.items() if keyword in normalized_prompt
    ]
    must_have = _normalize_text_list(
        [*hard_genres_labels(hard_genres), *narrative_targets[:2], *story_outcomes[:2], *character_dynamics[:2]]
    )
    nice_to_have = _normalize_text_list(
        [
            *soft_preferences,
            *tone[:3],
            *emotional_targets[:3],
            *themes[:3],
            *([pacing] if pacing else []),
            *([complexity] if complexity else []),
        ]
    )
    ending_type = _infer_ending_type(normalized_prompt, story_outcomes)
    violence_level = "low" if "not too scary" in normalized_prompt or "no gore" in normalized_prompt else None
    scale = "epic" if "epic" in normalized_prompt or "blockbuster" in normalized_prompt else "intimate" if "small" in normalized_prompt or "intimate" in normalized_prompt else None
    subgenres = _extract_subgenres(normalized_prompt)

    person_name = _extract_person_name(prompt)
    reference_title = _extract_reference_title(prompt)
    reference_titles = [reference_title] if reference_title else []
    query_type = (
        "person"
        if person_name
        else "title_similarity"
        if reference_titles
        else "anime"
        if wants_anime
        else "animation"
        if wants_animation
        else "mixed_constraints"
        if must_have and nice_to_have
        else "narrative"
        if story_outcomes or character_dynamics or ending_type
        else "mood"
        if soft_preferences or tone or themes
        else "year"
        if year and not hard_genres
        else "genre"
        if hard_genres
        else "general"
    )
    intent_family = _classify_intent_family(
        normalized_prompt=normalized_prompt,
        query_type=query_type,
        reference_titles=reference_titles,
        hard_genres=hard_genres,
        soft_preferences=soft_preferences,
        tone=tone,
        emotional_targets=emotional_targets,
        themes=themes,
        narrative_targets=narrative_targets,
        story_outcomes=story_outcomes,
        audience="family friendly" if "family friendly" in normalized_prompt else None,
        avoid_elements=avoid_elements,
    )
    if any(
        phrase in normalized_prompt
        for phrase in [
            "healing movie",
            "healing movie with heart",
            "emotionally healing",
            "cathartic",
            "emotional family drama",
            "family drama",
            "relationship-centered drama",
        ]
    ):
        intent_family = "sad_emotional"
    elif "make me cry" in normalized_prompt and (
        "love" in normalized_prompt or "romance" in normalized_prompt or "love story" in normalized_prompt
    ):
        intent_family = "mixed"
    retrieval_summary = _build_fallback_retrieval_summary(
        prompt=prompt,
        intent_family=intent_family,
        reference_titles=reference_titles,
        genres=hard_genres_labels(hard_genres),
        subgenres=subgenres,
        tone=tone,
        moods=soft_preferences,
        emotional_targets=emotional_targets,
        themes=themes,
        narrative_targets=narrative_targets,
        story_outcomes=story_outcomes,
        ending_type=ending_type,
        character_dynamics=character_dynamics,
        setting=setting,
        pacing=pacing,
        complexity=complexity,
        person=person_name,
        audience="family friendly" if "family friendly" in normalized_prompt else None,
    )

    return ParsedPrompt(
        intent_family=intent_family,
        year=year,
        hard_genres=hard_genres,
        soft_preferences=list(dict.fromkeys(soft_preferences)),
        tone=_normalize_text_list(tone),
        emotional_targets=_normalize_text_list(emotional_targets),
        themes=_normalize_text_list(themes),
        narrative_targets=_normalize_text_list(narrative_targets),
        story_outcomes=_normalize_text_list(story_outcomes),
        ending_type=ending_type,
        character_dynamics=_normalize_text_list(character_dynamics),
        setting=_normalize_text_list(setting),
        scale=scale,
        pacing=pacing,
        complexity=complexity,
        violence_level=violence_level,
        wants_anime=wants_anime,
        wants_animation=wants_animation or wants_anime,
        person_name=person_name,
        reference_titles=reference_titles,
        subgenres=subgenres,
        language=language,
        must_have=must_have,
        nice_to_have=nice_to_have,
        exclude_terms=[],
        avoid_genres=avoid_genres,
        avoid_elements=avoid_elements,
        release_preference=None,
        audience="family friendly" if "family friendly" in normalized_prompt else None,
        query_type=query_type,
        retrieval_summary=retrieval_summary,
    )


def hard_genres_labels(hard_genres: list[dict]) -> list[str]:
    return [genre["label"] for genre in hard_genres if genre.get("label")]


def _normalize_text_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for value in values:
        item = value.strip()
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(item)
    return normalized


def _infer_ending_type(normalized_prompt: str, story_outcomes: list[str]) -> str | None:
    if "villain wins" in normalized_prompt:
        return "villain victory"
    if "tragic ending" in normalized_prompt or "tragic" in normalized_prompt:
        return "tragic"
    if "happy ending" in normalized_prompt or "uplifting" in normalized_prompt:
        return "happy"
    if "bittersweet ending" in normalized_prompt or "bittersweet" in normalized_prompt:
        return "bittersweet"
    if any("ending" in value for value in story_outcomes):
        return story_outcomes[0]
    return None


def _extract_subgenres(normalized_prompt: str) -> list[str]:
    known = [
        "family drama",
        "psychological thriller",
        "space opera",
        "coming-of-age",
        "romantic drama",
        "political thriller",
        "crime drama",
    ]
    return [value for value in known if value in normalized_prompt]


def _build_fallback_retrieval_summary(
    *,
    prompt: str,
    intent_family: str,
    reference_titles: list[str],
    genres: list[str],
    subgenres: list[str],
    tone: list[str],
    moods: list[str],
    emotional_targets: list[str],
    themes: list[str],
    narrative_targets: list[str],
    story_outcomes: list[str],
    ending_type: str | None,
    character_dynamics: list[str],
    setting: list[str],
    pacing: str | None,
    complexity: str | None,
    person: str | None,
    audience: str | None,
) -> str:
    parts: list[str] = []
    if intent_family != "general":
        parts.append(f"intent family: {intent_family}")
    if reference_titles:
        parts.append(f"similar to {reference_titles[0]}")
    if person:
        parts.append(f"starring {person}")
    if genres:
        parts.append(", ".join(genres[:3]))
    if subgenres:
        parts.append(", ".join(subgenres[:2]))
    if tone:
        parts.append(f"tone: {', '.join(tone[:3])}")
    if moods:
        parts.append(f"mood: {', '.join(moods[:4])}")
    if emotional_targets:
        parts.append(f"emotional targets: {', '.join(emotional_targets[:4])}")
    if themes:
        parts.append(f"themes: {', '.join(themes[:3])}")
    if narrative_targets:
        parts.append(f"narrative targets: {', '.join(narrative_targets[:4])}")
    if story_outcomes:
        parts.append(f"story outcomes: {', '.join(story_outcomes[:2])}")
    if ending_type:
        parts.append(f"ending: {ending_type}")
    if character_dynamics:
        parts.append(f"character dynamics: {', '.join(character_dynamics[:2])}")
    if setting:
        parts.append(f"setting: {', '.join(setting[:2])}")
    if pacing:
        parts.append(f"pacing: {pacing}")
    if complexity:
        parts.append(f"complexity: {complexity}")
    if audience:
        parts.append(f"audience: {audience}")
    return "; ".join(parts) if parts else prompt


def _classify_intent_family(
    *,
    normalized_prompt: str,
    query_type: str,
    reference_titles: list[str],
    hard_genres: list[dict],
    soft_preferences: list[str],
    tone: list[str],
    emotional_targets: list[str],
    themes: list[str],
    narrative_targets: list[str],
    story_outcomes: list[str],
    audience: str | None,
    avoid_elements: list[str],
) -> str:
    if reference_titles or query_type == "title_similarity":
        return "reference"
    if query_type == "person":
        return "general"
    if narrative_targets or story_outcomes or "villain wins" in normalized_prompt or "ending" in normalized_prompt:
        return "narrative"
    if any(item in normalized_prompt for item in ["date night", "family night", "late night", "rainy day"]):
        return "use_case"
    if avoid_elements or "not too scary" in normalized_prompt or "no gore" in normalized_prompt or "no horror" in normalized_prompt:
        return "constraint"

    genre_ids = {genre["id"] for genre in hard_genres}
    romance_like = 10749 in genre_ids or "love" in normalized_prompt or "romantic" in tone
    healing_like = any(
        item in normalized_prompt
        for item in [
            "healing movie",
            "healing",
            "emotionally healing",
            "cathartic",
            "family drama",
            "relationship-centered drama",
            "warm but sad",
            "with heart",
        ]
    ) or any(
        value in emotional_targets for value in ["emotional healing", "emotional", "heartbreaking", "bittersweet"]
    ) and any(
        theme in themes for theme in ["family", "family conflict", "reconciliation", "forgiveness", "recovery"]
    )
    funny_like = 35 in genre_ids or any(
        item in soft_preferences for item in ["funny", "fun", "laugh-out-loud", "witty", "banter", "rom-com"]
    )
    sad_like = any(
        value in emotional_targets for value in ["sad", "emotional", "heartbreaking", "tragic", "bittersweet"]
    ) or any(
        item in soft_preferences for item in ["sad", "heartbreaking", "emotional", "depressing", "tragic"]
    ) or any(
        phrase in normalized_prompt
        for phrase in ["cry to", "crying", "make me cry", "movie to cry to", "tearjerker", "tear jerker"]
    )
    feel_good_like = any(
        phrase in normalized_prompt
        for phrase in ["feel good", "comfort movie", "cozy movie", "wholesome movie", "something warm and nice", "relaxed night"]
    ) or "uplifting" in tone or "cozy" in tone or any(
        value in emotional_targets for value in ["warm", "uplifting", "emotional healing", "cozy", "comfort", "wholesome", "relaxing", "easy watch"]
    )
    dark_like = any(item in soft_preferences for item in ["dark", "darker"]) or 53 in genre_ids or 27 in genre_ids

    active_families = [
        family
        for family, enabled in [
            ("romance", romance_like),
            ("sad_emotional", sad_like or healing_like),
            ("feel_good", feel_good_like),
            ("funny", funny_like),
            ("dark_intense", dark_like),
        ]
        if enabled
    ]
    if len(active_families) > 1:
        return "mixed"
    if active_families:
        return active_families[0]
    if audience == "family friendly":
        return "use_case"
    if query_type in {"mood", "mixed_constraints"}:
        return "mixed"
    return "general"


def _extract_person_name(prompt: str) -> str | None:
    patterns = [
        r"\bwith\s+([a-z]+(?:\s+[a-z]+){0,3})\s+in\s+it\b",
        r"\bstarring\s+([a-z]+(?:\s+[a-z]+){0,3})\b",
        r"\bmovie[s]?\s+with\s+([a-z]+(?:\s+[a-z]+){0,3})\b",
        r"\bfilm[s]?\s+with\s+([a-z]+(?:\s+[a-z]+){0,3})\b",
    ]
    normalized_prompt = prompt.lower()
    for pattern in patterns:
        match = re.search(pattern, normalized_prompt)
        if match:
            candidate = match.group(1).strip()
            return " ".join(part.capitalize() for part in candidate.split())
    return None


def _extract_reference_title(prompt: str) -> str | None:
    patterns = [
        r"\blike\s+(.+?)(?:\s+but\s+.+)?$",
        r"\bsimilar\s+to\s+(.+?)(?:\s+but\s+.+)?$",
    ]
    for pattern in patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if not match:
            continue
        candidate = match.group(1).strip(" .!?\"'")
        if candidate:
            return candidate
    return None


def _normalize_reference_title(title: str) -> str:
    cleaned = re.sub(r"\s+", " ", title).strip(" .!?,:;\"'")
    cleaned = re.sub(r"\b(movie|film|films|movies)\b", "", cleaned, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", cleaned).strip()


def _simplified_reference_tokens(title: str) -> list[str]:
    cleaned = _normalize_reference_title(title)
    variants: list[str] = []
    variants.append(cleaned)
    stripped = re.split(
        r"\b(?:but|with|that|where|which|and)\b",
        cleaned,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" -:,")
    if stripped and stripped != cleaned:
        variants.append(stripped)
    no_punctuation = re.sub(r"[^\w\s]", " ", stripped or cleaned)
    no_punctuation = re.sub(r"\s+", " ", no_punctuation).strip()
    if no_punctuation and no_punctuation not in variants:
        variants.append(no_punctuation)
    tokens = no_punctuation.split()
    if len(tokens) > 2:
        shortened = " ".join(tokens[: min(4, len(tokens))]).strip()
        if shortened and shortened not in variants:
            variants.append(shortened)
    return [variant for variant in variants if variant]


class TMDBService:
    _cache: dict[tuple, tuple[float, dict | list[dict] | None]] = {}

    def __init__(self) -> None:
        self.api_key = settings.tmdb_api_key.strip()
        self.base_url = settings.tmdb_base_url.rstrip("/")
        self.image_base_url = settings.tmdb_image_base_url.rstrip("/")
        self.timeout = httpx.Timeout(15.0, connect=10.0)
        self._client: httpx.Client | None = None
        self.embedding_service = EmbeddingService()
        self.intent_parser = IntentParserService()

    def get_recommendations(
        self,
        prompt: str,
        preferences: UserPreferenceResponse | None = None,
    ) -> RecommendationResponse:
        if not self.api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="TMDB_API_KEY is not configured.",
            )

        with httpx.Client(
            base_url=self.base_url,
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            timeout=self.timeout,
        ) as client:
            self._client = client
            parsed_prompt = self._parse_prompt(prompt)
            logger.debug("parsed_intent %s", self._family_debug_info(parsed_prompt))
            resolved_person = None
            reference_movie = None
            if parsed_prompt.person_name:
                try:
                    resolved_person = self._find_person(parsed_prompt.person_name)
                except HTTPException:
                    resolved_person = None
            if resolved_person is None and parsed_prompt.reference_titles:
                try:
                    reference_movie = self._find_reference_movie(parsed_prompt.reference_titles[0])
                except HTTPException:
                    reference_movie = None
            if resolved_person is not None:
                plans = self._build_person_group_plans(resolved_person)
            else:
                plans = self._build_group_plans(prompt, parsed_prompt, reference_movie)

            groups: list[RecommendationGroup] = []
            seen_movie_ids: set[int] = set()
            for plan in plans[:MAX_GROUPS]:
                group = self._fetch_group(plan, prompt, parsed_prompt, seen_movie_ids, preferences)
                if group is not None:
                    groups.append(group)
                    seen_movie_ids.update(movie.id for movie in group.movies)
            self._client = None

        if not groups:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="TMDB returned no movie results for the given prompt.",
            )

        summary = (
            f'{self._intent_summary(prompt, parsed_prompt)} '
            "TMDB remains the source of truth for final movie selection and ranking."
        )
        return RecommendationResponse(summary=summary, groups=groups)

    def _parse_prompt(self, prompt: str) -> ParsedPrompt:
        ai_intent = self.intent_parser.parse_intent(prompt)
        if ai_intent is None:
            return parse_prompt(prompt)
        return self._parsed_prompt_from_intent(ai_intent, prompt)

    def _parsed_prompt_from_intent(self, intent: MovieIntent, prompt: str) -> ParsedPrompt:
        fallback = parse_prompt(prompt)
        hard_genres: list[dict] = []
        seen_ids: set[int] = set()

        for genre in intent.genres:
            normalized_genre = genre.lower()
            if normalized_genre in GENRE_MAP:
                genre_config = GENRE_MAP[normalized_genre]
                if genre_config["id"] not in seen_ids:
                    hard_genres.append(genre_config)
                    seen_ids.add(genre_config["id"])

        if intent.animation and 16 not in seen_ids:
            hard_genres.append({"id": 16, "label": "Animation", "title": "Animated Picks"})
            seen_ids.add(16)

        retrieval_summary = self.intent_parser.build_retrieval_summary(intent)
        tone = list(dict.fromkeys(intent.tone or fallback.tone))
        moods = list(dict.fromkeys(intent.moods or fallback.soft_preferences))
        emotional_targets = list(dict.fromkeys(intent.emotional_targets or fallback.emotional_targets))
        combined_soft = list(dict.fromkeys([*moods, *tone]))
        must_have = list(dict.fromkeys(intent.must_have or fallback.must_have))
        nice_to_have = list(dict.fromkeys(intent.nice_to_have or fallback.nice_to_have))
        avoid_genres = list(dict.fromkeys(intent.avoid_genres or fallback.avoid_genres))
        avoid_elements = list(dict.fromkeys(intent.avoid_elements or fallback.avoid_elements))

        intent_family = intent.intent_family or fallback.intent_family
        if intent_family == "general" and fallback.intent_family != "general":
            intent_family = fallback.intent_family
        query_type = intent.query_type or fallback.query_type
        if query_type == "general" and fallback.query_type != "general":
            query_type = fallback.query_type

        return ParsedPrompt(
            intent_family=intent_family,
            year=intent.year if intent.year is not None else fallback.year,
            hard_genres=hard_genres or fallback.hard_genres,
            soft_preferences=combined_soft or fallback.soft_preferences,
            tone=tone or fallback.tone,
            emotional_targets=emotional_targets or fallback.emotional_targets,
            themes=list(dict.fromkeys(intent.themes or fallback.themes)),
            narrative_targets=list(dict.fromkeys(intent.narrative_targets or fallback.narrative_targets)),
            story_outcomes=list(dict.fromkeys(intent.story_outcomes or fallback.story_outcomes)),
            ending_type=intent.ending_type or fallback.ending_type,
            character_dynamics=list(dict.fromkeys(intent.character_dynamics or fallback.character_dynamics)),
            setting=list(dict.fromkeys(intent.setting or fallback.setting)),
            scale=intent.scale or fallback.scale,
            pacing=intent.pacing or fallback.pacing,
            complexity=intent.complexity or fallback.complexity,
            violence_level=intent.violence_level or fallback.violence_level,
            wants_anime=bool(intent.anime or fallback.wants_anime),
            wants_animation=bool(intent.animation or fallback.wants_animation or intent.anime),
            person_name=intent.person or fallback.person_name,
            reference_titles=intent.reference_titles or fallback.reference_titles,
            subgenres=list(dict.fromkeys(intent.subgenres or fallback.subgenres)),
            language=intent.language or fallback.language,
            must_have=must_have,
            nice_to_have=nice_to_have,
            exclude_terms=intent.exclude_terms or fallback.exclude_terms,
            avoid_genres=avoid_genres,
            avoid_elements=avoid_elements,
            release_preference=intent.release_preference or fallback.release_preference,
            audience=intent.audience or fallback.audience,
            query_type=query_type,
            retrieval_summary=retrieval_summary or fallback.retrieval_summary,
        )

    def _build_person_group_plans(self, person: dict) -> list[GroupPlan]:
        person_id = person["id"]
        person_name = person["name"]
        return [
            GroupPlan(
                key=f"person-best-{person_id}",
                title=f"Best Match: {person_name} Movies",
                description=f"Released movies from TMDB credits for {person_name}, ranked for strongest overall match.",
                mode="person_best",
                person_id=person_id,
                person_name=person_name,
            ),
            GroupPlan(
                key=f"person-popular-{person_id}",
                title=f"Popular {person_name} Movies",
                description=f"High-popularity TMDB movie credits featuring {person_name}.",
                mode="person_popular",
                person_id=person_id,
                person_name=person_name,
            ),
            GroupPlan(
                key=f"person-hidden-{person_id}",
                title=f"Hidden Gems from {person_name}",
                description=f"Lower-exposure TMDB movie credits featuring {person_name}.",
                mode="person_hidden",
                person_id=person_id,
                person_name=person_name,
            ),
        ][:MAX_GROUPS]

    def _build_group_plans(
        self,
        prompt: str,
        parsed_prompt: ParsedPrompt,
        reference_movie: dict | None = None,
    ) -> list[GroupPlan]:
        plans: list[GroupPlan] = []

        family_defaults = self._family_defaults(parsed_prompt)
        primary_genre_id = parsed_prompt.hard_genres[0]["id"] if parsed_prompt.hard_genres else family_defaults["default_genre_id"]
        if primary_genre_id is None and self._prefers_sad_drama(parsed_prompt):
            primary_genre_id = 18
        primary_description = "The closest TMDB discover match for your full request."
        primary_mode = "discover"
        primary_query: str | None = None
        if reference_movie is not None:
            primary_mode = "similar"
            primary_description = (
                f'Similar movies anchored to {reference_movie["title"]} and refined by your parsed preferences.'
            )
        elif parsed_prompt.reference_titles:
            primary_mode = "search"
            primary_query = self._reference_query(parsed_prompt)
            primary_description = (
                f'Search results anchored to {parsed_prompt.reference_titles[0]} and refined by your parsed preferences.'
            )
        elif parsed_prompt.year is not None and primary_genre_id is not None:
            primary_description = f"Best match discover results filtered by genre and year {parsed_prompt.year}."
        elif parsed_prompt.year is not None:
            primary_description = f"Best match discover results filtered to releases from {parsed_prompt.year}."
        elif primary_genre_id is not None:
            primary_description = "Best match discover results filtered to your explicit genre request."

        plans.append(
            GroupPlan(
                key="best-match",
                title="Best Match",
                description=primary_description,
                mode=primary_mode,
                year=parsed_prompt.year,
                genre_id=primary_genre_id,
                query=primary_query,
                original_language="ja" if parsed_prompt.wants_anime else None,
                min_vote_count=50 if parsed_prompt.year is not None else 100,
                reference_movie_id=reference_movie["id"] if reference_movie is not None else None,
                reference_movie_title=reference_movie["title"] if reference_movie is not None else None,
            )
        )

        if parsed_prompt.year is not None:
            plans.append(
                GroupPlan(
                    key=f"year-trending-{parsed_prompt.year}",
                    title=f"Trending {parsed_prompt.year}",
                    description=f"Popular TMDB picks released in {parsed_prompt.year}.",
                    mode="discover",
                    year=parsed_prompt.year,
                    genre_id=primary_genre_id,
                    original_language="ja" if parsed_prompt.wants_anime else None,
                    sort_by="popularity.desc",
                    min_vote_count=50,
                )
            )
            plans.append(
                GroupPlan(
                    key=f"year-hidden-{parsed_prompt.year}",
                    title=f"Because You Said {parsed_prompt.year}",
                    description=f"Strong TMDB matches narrowed to releases from {parsed_prompt.year}.",
                    mode="discover",
                    year=parsed_prompt.year,
                    genre_id=primary_genre_id,
                    original_language="ja" if parsed_prompt.wants_anime else None,
                    sort_by="vote_average.desc",
                    min_vote_count=20,
                    max_vote_count=250,
                )
            )

        if parsed_prompt.wants_anime:
            plans.append(
                GroupPlan(
                    key="anime-picks",
                    title="Anime Picks",
                    description="Animation results biased toward anime-friendly TMDB discover filters.",
                    mode="discover",
                    year=parsed_prompt.year,
                    genre_id=16,
                    original_language="ja",
                    sort_by="popularity.desc",
                    min_vote_count=20,
                )
            )
        elif parsed_prompt.wants_animation:
            plans.append(
                GroupPlan(
                    key="animated-picks",
                    title="Animated Picks",
                    description="Animation results that stay aligned with your explicit animation request.",
                    mode="discover",
                    year=parsed_prompt.year,
                    genre_id=16,
                    sort_by="popularity.desc",
                    min_vote_count=20,
                )
            )

        if parsed_prompt.year is not None or parsed_prompt.hard_genres:
            hidden_title = (
                f"Hidden Gems from {parsed_prompt.year}"
                if parsed_prompt.year is not None
                else "Hidden Gems"
            )
            hidden_description = (
                f"Less obvious TMDB picks that still respect your explicit filters from {parsed_prompt.year}."
                if parsed_prompt.year is not None
                else "Less obvious TMDB picks that still respect your explicit filters."
            )
            plans.append(
                GroupPlan(
                    key="hidden-gems",
                    title=hidden_title,
                    description=hidden_description,
                    mode="discover",
                    year=parsed_prompt.year,
                    genre_id=primary_genre_id,
                    original_language="ja" if parsed_prompt.wants_anime else None,
                    sort_by="vote_average.desc",
                    min_vote_count=15,
                    max_vote_count=180,
                )
            )

        if parsed_prompt.wants_animation:
            trending_animation_title = (
                "Trending Anime" if parsed_prompt.wants_anime else "Trending Animation"
            )
            plans.append(
                GroupPlan(
                    key="trending-animation",
                    title=trending_animation_title,
                    description="Popular TMDB animation picks that stay within the requested animation lane.",
                    mode="discover",
                    year=parsed_prompt.year,
                    genre_id=16,
                    original_language="ja" if parsed_prompt.wants_anime else None,
                    sort_by="popularity.desc",
                    min_vote_count=20,
                )
            )

        if not parsed_prompt.year and not parsed_prompt.hard_genres:
            if self._prefers_sad_drama(parsed_prompt):
                plans.append(
                    GroupPlan(
                        key="emotional-dramas",
                        title="Emotional Dramas",
                        description="Drama-first picks tuned for grief, heartbreak, memory, and introspective emotional weight.",
                        mode="discover",
                        genre_id=18,
                        sort_by="vote_average.desc",
                        min_vote_count=120,
                        max_vote_count=1200,
                    )
                )
                plans.append(
                    GroupPlan(
                        key="heartfelt-picks",
                        title="Heartfelt Picks",
                        description="High-quality romantic and family-adjacent dramas for sad or reflective movie nights.",
                        mode="discover",
                        genre_id=10749,
                        sort_by="vote_average.desc",
                        min_vote_count=80,
                        max_vote_count=900,
                    )
                )
                if self._healing_prompt(parsed_prompt):
                    plans.append(
                        GroupPlan(
                            key="healing-arcs",
                            title="Healing Arcs",
                            description="Drama and family-centered fallback picks with reconciliation, recovery, and heart-forward emotional payoff.",
                            mode="discover",
                            genre_id=10751,
                            sort_by="vote_average.desc",
                            min_vote_count=60,
                            max_vote_count=850,
                        )
                    )
            elif parsed_prompt.intent_family == "romance":
                plans.append(
                    GroupPlan(
                        key="romance-fallback",
                        title="Romance Essentials",
                        description="Romance-forward fallback picks with relationship-centered drama and warmth.",
                        mode="discover",
                        genre_id=10749,
                        sort_by="vote_average.desc",
                        min_vote_count=100,
                    )
                )
                plans.append(
                    GroupPlan(
                        key="romance-light",
                        title="Warm Relationship Picks",
                        description="Accessible romantic dramas and rom-com adjacent picks for romance-first prompts.",
                        mode="discover",
                        genre_id=18,
                        sort_by="vote_average.desc",
                        min_vote_count=80,
                    )
                )
            elif parsed_prompt.intent_family == "funny":
                funny_preferences = set(parsed_prompt.soft_preferences) | set(parsed_prompt.tone)
                plans.append(
                    GroupPlan(
                        key="funny-fallback",
                        title="Comedy Favorites",
                        description="Comedy-led fallback picks for laughs and lighter pacing.",
                        mode="discover",
                        genre_id=35,
                        sort_by="popularity.desc",
                        min_vote_count=120,
                    )
                )
                plans.append(
                    GroupPlan(
                        key="funny-light",
                        title="Easy Watches",
                        description="Lighter comedy and adventure-adjacent movies for funny prompts.",
                        mode="discover",
                        genre_id=10749 if "rom-com" in funny_preferences or "romantic" in funny_preferences else 12,
                        sort_by="vote_average.desc",
                        min_vote_count=100,
                    )
                )
                if {"rom-com", "banter", "witty"} & funny_preferences:
                    plans.append(
                        GroupPlan(
                            key="funny-romcom",
                            title="Rom-Com Chemistry",
                            description="Romance-comedy fallback picks with banter, chemistry, and lighter tone.",
                            mode="discover",
                            genre_id=10749,
                            sort_by="vote_average.desc",
                            min_vote_count=100,
                        )
                    )
            elif parsed_prompt.intent_family == "feel_good":
                plans.append(
                    GroupPlan(
                        key="feel-good-fallback",
                        title="Feel-Good Picks",
                        description="Comforting crowd-pleasers with lighter tone and warm payoff.",
                        mode="discover",
                        genre_id=35,
                        sort_by="vote_average.desc",
                        min_vote_count=100,
                    )
                )
                plans.append(
                    GroupPlan(
                        key="feel-good-heart",
                        title="Warm Crowd-Pleasers",
                        description="Family, romance, and adventure-adjacent fallback picks for feel-good prompts.",
                        mode="discover",
                        genre_id=10749,
                        sort_by="popularity.desc",
                        min_vote_count=80,
                    )
                )
            elif parsed_prompt.intent_family == "dark_intense":
                plans.append(
                    GroupPlan(
                        key="dark-fallback",
                        title="Dark Intense Picks",
                        description="Thriller and mystery fallback picks for darker, more intense prompts.",
                        mode="discover",
                        genre_id=53,
                        sort_by="vote_average.desc",
                        min_vote_count=100,
                    )
                )
                plans.append(
                    GroupPlan(
                        key="dark-mystery",
                        title="Mystery Pressure",
                        description="Moodier mystery and drama fallback picks for dark-intense queries.",
                        mode="discover",
                        genre_id=9648,
                        sort_by="vote_average.desc",
                        min_vote_count=80,
                    )
                )
            elif parsed_prompt.intent_family == "use_case":
                use_case_genre_id = family_defaults["default_genre_id"] or 10749
                plans.append(
                    GroupPlan(
                        key="use-case-fallback",
                        title="Use-Case Picks",
                        description="Fallback picks shaped around the implied movie-night use case.",
                        mode="discover",
                        genre_id=use_case_genre_id,
                        sort_by="vote_average.desc",
                        min_vote_count=80,
                    )
                )
            elif parsed_prompt.intent_family == "constraint":
                plans.append(
                    GroupPlan(
                        key="constraint-fallback",
                        title="Constraint-Friendly Picks",
                        description="Fallback picks that stay within the requested restrictions and exclusions.",
                        mode="discover",
                        genre_id=primary_genre_id,
                        sort_by="vote_average.desc",
                        min_vote_count=100,
                    )
                )
            else:
                plans.append(
                    GroupPlan(
                        key="trending-now",
                        title="Trending Now",
                        description="Popular TMDB movies when the request is broad and open-ended.",
                        mode="discover",
                        sort_by="popularity.desc",
                        min_vote_count=250,
                    )
                )
                plans.append(
                    GroupPlan(
                        key="new-releases",
                        title="New Releases",
                        description="Recent TMDB discover picks for broad recommendation prompts.",
                        mode="discover",
                        sort_by="primary_release_date.desc",
                        min_vote_count=40,
                    )
                )
                plans.append(
                    GroupPlan(
                        key="hidden-gems-broad",
                        title="Hidden Gems",
                        description="Less obvious TMDB picks for broader recommendation prompts.",
                        mode="discover",
                        sort_by="vote_average.desc",
                        min_vote_count=20,
                        max_vote_count=220,
                    )
                )

        deduped_plans: list[GroupPlan] = []
        seen_keys: set[str] = set()
        for plan in plans:
            if plan.key in seen_keys:
                continue
            seen_keys.add(plan.key)
            deduped_plans.append(plan)
        return deduped_plans[:MAX_GROUPS]

    def _fetch_group(
        self,
        plan: GroupPlan,
        prompt: str,
        parsed_prompt: ParsedPrompt,
        seen_movie_ids: set[int],
        preferences: UserPreferenceResponse | None = None,
    ) -> RecommendationGroup | None:
        if plan.mode.startswith("person_"):
            results = self._person_movies(plan)
        elif plan.mode == "similar" and plan.reference_movie_id is not None:
            results = self._similar_candidate_pool(plan.reference_movie_id, parsed_prompt)
            if not results:
                results = self._reference_recovery_pool(parsed_prompt) or self._discover_movies(
                    genre_id=plan.genre_id,
                    year=plan.year,
                    original_language=plan.original_language,
                    sort_by=plan.sort_by,
                    min_vote_count=plan.min_vote_count,
                    max_vote_count=plan.max_vote_count,
                )
        elif plan.mode == "discover":
            results = self._discover_movies(
                genre_id=plan.genre_id,
                year=plan.year,
                original_language=plan.original_language,
                sort_by=plan.sort_by,
                min_vote_count=plan.min_vote_count,
                max_vote_count=plan.max_vote_count,
            )
        else:
            query = plan.query or prompt
            results = self._search_movies(query)
            if not results:
                hint_query = self._extract_hint_query(parsed_prompt)
                if hint_query and hint_query != query:
                    results = self._search_movies(hint_query)

        if not results:
            results = self._recover_results(plan, prompt, parsed_prompt)
        if not results:
            return None

        strict_intent = plan.key == "best-match" or plan.mode == "person_best"
        if plan.mode == "similar":
            results = self._clean_similar_results(results, parsed_prompt, strict=strict_intent)
            if strict_intent and len(results) < 4:
                fallback_results = results or self._similar_candidate_pool(
                    plan.reference_movie_id or 0,
                    parsed_prompt,
                )
                if len(fallback_results) < 4:
                    fallback_results = [*fallback_results, *self._reference_recovery_pool(parsed_prompt)]
                results = self._clean_similar_results(fallback_results, parsed_prompt, strict=False)
            if not results:
                return None

        intent_filtered_results = self._apply_intent_filters(
            results[:MAX_CANDIDATES],
            parsed_prompt,
            strict=strict_intent,
        )
        if strict_intent and not intent_filtered_results:
            return None

        candidate_pool = intent_filtered_results or results[:MAX_CANDIDATES]
        candidate_pool = self._apply_quality_filters(candidate_pool, parsed_prompt, strict_intent)
        candidate_pool = self._apply_family_filter(candidate_pool, parsed_prompt, strict_intent)
        if strict_intent and not candidate_pool:
            candidate_pool = self._recover_results(plan, prompt, parsed_prompt)
            candidate_pool = self._apply_quality_filters(candidate_pool, parsed_prompt, False)
            candidate_pool = self._apply_family_filter(candidate_pool, parsed_prompt, False)
        if strict_intent and not candidate_pool:
            return None
        ranked_results = self._rank_movies(
            candidate_pool,
            parsed_prompt,
            plan.mode,
            primary=plan.key == "best-match",
        )
        ranked_results = self._embedding_rerank(ranked_results, prompt, parsed_prompt, plan)
        ranked_results = self._personalize_rerank(ranked_results, parsed_prompt, preferences)
        ranked_results = self._apply_exclusions(ranked_results, parsed_prompt)
        ranked_results = self._enforce_family_coherence(ranked_results, parsed_prompt)
        filtered_results = [
            movie for movie in ranked_results
            if movie.get("id") not in seen_movie_ids
        ]
        if not filtered_results:
            return None
        selected_movies = filtered_results[:MAX_MOVIES_PER_GROUP]
        if plan.key == "best-match" or plan.mode == "person_best":
            self._enrich_top_movies(selected_movies[:DETAILS_ENRICH_COUNT])
        movies = [self._normalize_movie(movie, prompt, parsed_prompt) for movie in selected_movies]
        if not movies:
            return None

        return RecommendationGroup(
            group_title=plan.title,
            description=plan.description,
            movies=movies,
        )

    def _discover_movies(
        self,
        genre_id: int | None,
        year: int | None = None,
        original_language: str | None = None,
        sort_by: str = "popularity.desc",
        min_vote_count: int = 100,
        max_vote_count: int | None = None,
    ) -> list[dict]:
        params = {
            "sort_by": sort_by,
            "include_adult": "false",
            "include_video": "false",
            "language": "en-US",
            "page": 1,
            "vote_count.gte": min_vote_count,
        }
        if genre_id is not None:
            params["with_genres"] = genre_id
        if year is not None:
            params["primary_release_year"] = year
        if original_language is not None:
            params["with_original_language"] = original_language
        if max_vote_count is not None:
            params["vote_count.lte"] = max_vote_count
        payload = self._request("/discover/movie", params)
        return self._filter_movies(payload.get("results", []))

    def _search_movies(self, query: str) -> list[dict]:
        payload = self._request(
            "/search/movie",
            {
                "query": query,
                "include_adult": "false",
                "language": "en-US",
                "page": 1,
            },
        )
        return self._filter_movies(payload.get("results", []))

    def _recover_results(
        self,
        plan: GroupPlan,
        prompt: str,
        parsed_prompt: ParsedPrompt,
    ) -> list[dict]:
        recovered: list[dict] = []
        for query in self._recovery_search_queries(plan, prompt, parsed_prompt):
            recovered.extend(self._search_movies(query))
            if len(self._filter_movies(recovered)) >= 6:
                break
        if recovered:
            return self._filter_movies(recovered)[:MAX_CANDIDATES]

        family_pool = self._family_recovery_pool(parsed_prompt)
        if family_pool:
            return family_pool[:MAX_CANDIDATES]

        return self._theme_recovery_pool(parsed_prompt)[:MAX_CANDIDATES]

    def _find_person(self, person_name: str | None) -> dict | None:
        if not person_name:
            return None
        payload = self._request(
            "/search/person",
            {
                "query": person_name,
                "include_adult": "false",
                "language": "en-US",
                "page": 1,
            },
        )
        results = payload.get("results", [])
        if not results:
            return None
        return results[0]

    def _person_movie_credits(self, person_id: int) -> list[dict]:
        payload = self._request(f"/person/{person_id}/movie_credits", {"language": "en-US"})
        cast_movies = payload.get("cast", [])
        return self._filter_movies(cast_movies)

    def _person_movies(self, plan: GroupPlan) -> list[dict]:
        if plan.person_id is None:
            return []
        movies = self._person_movie_credits(plan.person_id)
        today = int(date.today().strftime("%Y%m%d"))

        def release_key(movie: dict) -> int:
            release_date = (movie.get("release_date") or "").replace("-", "")
            return int(release_date) if release_date.isdigit() else 0

        enriched_movies = []
        for movie in movies[:MAX_CANDIDATES]:
            if not self._is_valid_person_movie(movie, today):
                continue
            enriched_movies.append(movie)

        if plan.mode == "person_best":
            return sorted(enriched_movies, key=self._person_best_score, reverse=True)
        if plan.mode == "person_popular":
            return sorted(enriched_movies, key=self._person_popular_score, reverse=True)
        if plan.mode == "person_hidden":
            return [
                movie
                for movie in sorted(enriched_movies, key=self._person_hidden_score, reverse=True)
                if float(movie.get("popularity") or 0.0) < 55
            ]
        return enriched_movies

    def _normalize_movie(self, movie: dict, prompt: str, parsed_prompt: ParsedPrompt) -> MovieRecommendation:
        details = movie.get("_details") or {}
        genre_names = self._genre_names(details.get("genres"), movie.get("genre_ids"))
        release_date = movie.get("release_date") or details.get("release_date") or ""
        year = int(release_date[:4]) if len(release_date) >= 4 and release_date[:4].isdigit() else 0
        runtime_value = details.get("runtime")
        runtime = f"{runtime_value // 60}h {runtime_value % 60:02d}m" if runtime_value else None
        overview = movie.get("overview") or details.get("overview") or "No overview available."
        tagline = details.get("tagline") or overview[:110]
        poster_url = self._image_url(movie.get("poster_path") or details.get("poster_path"))
        backdrop_url = self._image_url(movie.get("backdrop_path") or details.get("backdrop_path"))

        return MovieRecommendation(
            id=movie["id"],
            title=movie.get("title") or details.get("title") or "Unknown title",
            year=year,
            genre=", ".join(genre_names) if genre_names else "Movie",
            runtime=runtime,
            rating=round(float(movie.get("vote_average") or details.get("vote_average") or 0.0), 1),
            tagline=tagline,
            reason=self._build_reason(prompt, parsed_prompt, genre_names, overview),
            poster_url=poster_url,
            backdrop_url=backdrop_url,
        )

    def _movie_details(self, movie_id: int) -> dict:
        cache_key = ("movie_details", movie_id)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        payload = self._request(f"/movie/{movie_id}", {"language": "en-US"})
        self._cache_set(cache_key, payload)
        return payload

    def _is_valid_person_movie(self, movie: dict, today: int) -> bool:
        if not movie.get("poster_path"):
            return False
        vote_count = int(movie.get("vote_count") or 0)
        if vote_count < 50:
            return False

        release_date = (movie.get("release_date") or "").replace("-", "")
        if not release_date.isdigit() or int(release_date) > today:
            return False

        title_blob = " ".join(
            filter(
                None,
                [
                    movie.get("title"),
                    movie.get("original_title"),
                    movie.get("overview"),
                ],
            )
        ).lower()
        blocked_terms = [
            "behind the scenes",
            "making of",
            "documentary",
            "short film",
            "compilation",
            "featurette",
            "special",
        ]
        if any(term in title_blob for term in blocked_terms):
            return False

        genre_ids = set(movie.get("genre_ids") or [])
        if 99 in genre_ids:
            return False
        return True

    def _request(self, path: str, params: dict) -> dict:
        cache_key = (path, tuple(sorted(params.items())))
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        try:
            client = self._client
            if client is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="TMDB client is not initialized.",
                )
            response = client.get(path, params=params)
            response.raise_for_status()
            payload = response.json()
            self._cache_set(cache_key, payload)
            return payload
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"TMDB request failed with status {exc.response.status_code}.",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to reach TMDB.",
            ) from exc

    def _find_reference_movie(self, title: str) -> dict | None:
        cache_key = ("reference_movie", title.lower())
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        variants = self._reference_resolution_queries(title)
        movie = None
        for query in variants:
            results = self._search_movies(query)
            if results:
                movie = self._pick_best_reference_match(query, results)
                if movie is not None:
                    break
        self._cache_set(cache_key, movie)
        return movie

    def _reference_resolution_queries(self, title: str) -> list[str]:
        queries: list[str] = []
        normalized = _normalize_reference_title(title)
        queries.append(title.strip())
        if normalized and normalized not in queries:
            queries.append(normalized)
        for variant in _simplified_reference_tokens(title):
            if variant not in queries:
                queries.append(variant)
        stripped = re.split(r"\b(?:but|with|where|that|which|and)\b", normalized, maxsplit=1, flags=re.IGNORECASE)[0].strip(" -:,")
        if stripped and stripped not in queries:
            queries.append(stripped)
        token_query = " ".join([token for token in re.sub(r"[^\w\s]", " ", normalized).split()[:4] if token])
        if token_query and token_query not in queries:
            queries.append(token_query)
        return [query for query in queries if query]

    def _pick_best_reference_match(self, query: str, results: list[dict]) -> dict | None:
        normalized_query = _normalize_reference_title(query).lower()

        def match_score(movie: dict) -> tuple[float, float, float]:
            title = str(movie.get("title") or "").strip().lower()
            original_title = str(movie.get("original_title") or "").strip().lower()
            popularity = float(movie.get("popularity") or 0.0)
            vote_count = float(movie.get("vote_count") or 0.0)
            exact = 1.0 if normalized_query in {title, original_title} else 0.0
            starts = 1.0 if title.startswith(normalized_query) or original_title.startswith(normalized_query) else 0.0
            token_overlap = len(set(normalized_query.split()) & (set(title.split()) | set(original_title.split())))
            return (exact + starts + token_overlap, vote_count, popularity)

        ranked = sorted(results, key=match_score, reverse=True)
        return ranked[0] if ranked else None

    def _similar_movies(self, movie_id: int) -> list[dict]:
        payload = self._request(
            f"/movie/{movie_id}/similar",
            {"page": 1},
        )
        return self._filter_movies(payload.get("results", []))[:MAX_CANDIDATES]

    def _recommended_movies(self, movie_id: int) -> list[dict]:
        payload = self._request(
            f"/movie/{movie_id}/recommendations",
            {"page": 1},
        )
        return self._filter_movies(payload.get("results", []))[:MAX_CANDIDATES]

    def _similar_candidate_pool(
        self,
        movie_id: int,
        parsed_prompt: ParsedPrompt,
    ) -> list[dict]:
        reference_genre_ids = list(self._reference_genre_ids(parsed_prompt))
        primary_genre_id = 878 if 878 in reference_genre_ids else (reference_genre_ids[0] if reference_genre_ids else None)

        similar_movies = self._similar_movies(movie_id)
        recommended_movies = self._recommended_movies(movie_id)
        genre_discover_movies = self._discover_movies(
            genre_id=primary_genre_id,
            year=parsed_prompt.year,
            original_language="ja" if parsed_prompt.wants_anime else None,
            sort_by="vote_count.desc",
            min_vote_count=200,
        ) if primary_genre_id is not None else []
        high_quality_fallback = self._discover_movies(
            genre_id=primary_genre_id,
            year=parsed_prompt.year,
            original_language="ja" if parsed_prompt.wants_anime else None,
            sort_by="vote_average.desc",
            min_vote_count=300,
        ) if primary_genre_id is not None else []
        recovery_discover = self._discover_movies(
            genre_id=primary_genre_id,
            year=parsed_prompt.year,
            original_language="ja" if parsed_prompt.wants_anime else None,
            sort_by="popularity.desc",
            min_vote_count=150,
        ) if primary_genre_id is not None else []

        merged: list[dict] = []
        seen_ids: set[int] = set()
        for source in (
            similar_movies,
            recommended_movies,
            genre_discover_movies,
            high_quality_fallback,
            recovery_discover,
        ):
            for movie in source:
                movie_id_value = movie.get("id")
                if not movie_id_value or movie_id_value in seen_ids:
                    continue
                seen_ids.add(movie_id_value)
                merged.append(movie)
                if len(merged) >= MAX_SIMILAR_CANDIDATES:
                    return merged
        return merged

    def _reference_recovery_pool(self, parsed_prompt: ParsedPrompt) -> list[dict]:
        reference_genre_ids = list(self._reference_genre_ids(parsed_prompt))
        primary_genre_id = 878 if 878 in reference_genre_ids else (reference_genre_ids[0] if reference_genre_ids else None)
        if primary_genre_id is None:
            primary_genre_id = parsed_prompt.hard_genres[0]["id"] if parsed_prompt.hard_genres else None
        if primary_genre_id is None:
            return []

        broad = self._discover_movies(
            genre_id=primary_genre_id,
            year=parsed_prompt.year,
            original_language="ja" if parsed_prompt.wants_anime else None,
            sort_by="vote_count.desc",
            min_vote_count=120,
        )
        quality = self._discover_movies(
            genre_id=primary_genre_id,
            year=parsed_prompt.year,
            original_language="ja" if parsed_prompt.wants_anime else None,
            sort_by="vote_average.desc",
            min_vote_count=220,
        )

        merged: list[dict] = []
        seen_ids: set[int] = set()
        for source in (broad, quality):
            for movie in source:
                movie_id_value = movie.get("id")
                if not movie_id_value or movie_id_value in seen_ids:
                    continue
                seen_ids.add(movie_id_value)
                merged.append(movie)
                if len(merged) >= MAX_SIMILAR_CANDIDATES:
                    return merged
        return merged

    def _family_recovery_pool(self, parsed_prompt: ParsedPrompt) -> list[dict]:
        genre_candidates = self._family_recovery_genre_ids(parsed_prompt)
        merged: list[dict] = []
        seen_ids: set[int] = set()
        for genre_id in genre_candidates:
            source = self._discover_movies(
                genre_id=genre_id,
                year=parsed_prompt.year,
                original_language="ja" if parsed_prompt.wants_anime else None,
                sort_by="vote_average.desc",
                min_vote_count=80,
                max_vote_count=1400,
            )
            for movie in source:
                movie_id_value = movie.get("id")
                if not movie_id_value or movie_id_value in seen_ids:
                    continue
                seen_ids.add(movie_id_value)
                merged.append(movie)
                if len(merged) >= MAX_CANDIDATES:
                    return merged
        return merged

    def _theme_recovery_pool(self, parsed_prompt: ParsedPrompt) -> list[dict]:
        genre_candidates = self._theme_recovery_genre_ids(parsed_prompt)
        merged: list[dict] = []
        seen_ids: set[int] = set()
        for genre_id in genre_candidates:
            source = self._discover_movies(
                genre_id=genre_id,
                year=parsed_prompt.year,
                original_language="ja" if parsed_prompt.wants_anime else None,
                sort_by="popularity.desc",
                min_vote_count=60,
                max_vote_count=1200,
            )
            for movie in source:
                movie_id_value = movie.get("id")
                if not movie_id_value or movie_id_value in seen_ids:
                    continue
                seen_ids.add(movie_id_value)
                merged.append(movie)
                if len(merged) >= MAX_CANDIDATES:
                    return merged
        return merged

    def _filter_movies(self, movies: Iterable[dict]) -> list[dict]:
        filtered = []
        seen_ids: set[int] = set()
        for movie in movies:
            movie_id = movie.get("id")
            if not movie_id or movie_id in seen_ids:
                continue
            if not movie.get("title"):
                continue
            seen_ids.add(movie_id)
            filtered.append(movie)
        return filtered

    def _person_best_score(self, movie: dict) -> tuple[int, float, float, int]:
        vote_count = int(movie.get("vote_count") or 0)
        popularity = float(movie.get("popularity") or 0.0)
        vote_average = float(movie.get("vote_average") or 0.0)
        release_date = movie.get("release_date") or ""
        release_boost = int(release_date.replace("-", "")) if release_date else 0
        return (vote_count, popularity, vote_average, release_boost)

    def _person_popular_score(self, movie: dict) -> tuple[float, int, float]:
        popularity = float(movie.get("popularity") or 0.0)
        vote_count = int(movie.get("vote_count") or 0)
        vote_average = float(movie.get("vote_average") or 0.0)
        return (popularity, vote_count, vote_average)

    def _person_recent_score(self, movie: dict) -> tuple[int, int, float]:
        release_date = movie.get("release_date") or ""
        release_sort = int(release_date.replace("-", "")) if release_date else 0
        vote_count = int(movie.get("vote_count") or 0)
        popularity = float(movie.get("popularity") or 0.0)
        return (release_sort, vote_count, popularity)

    def _person_hidden_score(self, movie: dict) -> tuple[float, int, float]:
        vote_average = float(movie.get("vote_average") or 0.0)
        vote_count = int(movie.get("vote_count") or 0)
        popularity_penalty = -float(movie.get("popularity") or 0.0)
        return (vote_average, vote_count, popularity_penalty)

    def _rank_movies(
        self,
        movies: list[dict],
        parsed_prompt: ParsedPrompt,
        mode: str,
        primary: bool = False,
    ) -> list[dict]:
        reference_genre_ids = self._reference_genre_ids(parsed_prompt)
        required_genre_ids = self._required_genre_ids(parsed_prompt)
        family_defaults = self._family_defaults(parsed_prompt)

        def score(movie: dict) -> float:
            haystack = self._movie_haystack(movie)
            movie_genre_ids = self._movie_genre_ids(movie)
            details = movie.get("_details") or {}
            score_value = 0.0

            score_value += 8.0 * len(movie_genre_ids & required_genre_ids)
            if required_genre_ids and movie_genre_ids & required_genre_ids:
                score_value += 6.0

            secondary_matches = self._secondary_genre_match_count(movie_genre_ids, parsed_prompt)
            score_value += 2.5 * secondary_matches

            reference_overlap = len(movie_genre_ids & reference_genre_ids)
            if parsed_prompt.reference_titles:
                score_value += 4.0 * reference_overlap
                if reference_genre_ids and reference_overlap == 0:
                    score_value -= 10.0

            vote_count = float(movie.get("vote_count") or 0.0)
            vote_average = float(movie.get("vote_average") or 0.0)
            popularity = float(movie.get("popularity") or 0.0)
            score_value += min(vote_count / 150.0, 20.0)
            score_value += vote_average * 1.8
            score_value += min(popularity / 20.0, 8.0)

            if movie.get("poster_path"):
                score_value += 2.0
            runtime = details.get("runtime")
            if runtime is not None:
                if runtime >= 80:
                    score_value += 2.0
                elif runtime < 40:
                    score_value -= 8.0

            if self._is_released_movie(movie):
                score_value += 2.0
            elif parsed_prompt.query_type == "general":
                score_value -= 8.0

            if parsed_prompt.audience and parsed_prompt.audience.lower() in haystack:
                score_value += 2.0

            score_value += self._mood_score(parsed_prompt, movie_genre_ids, haystack)
            score_value += self._emotion_score(parsed_prompt, movie_genre_ids, haystack, primary=primary)
            score_value += self._narrative_score(parsed_prompt, movie_genre_ids, haystack, primary=primary)
            score_value += self._scifi_quality_score(parsed_prompt, movie_genre_ids, haystack)
            score_value += self._generic_penalty(parsed_prompt, movie_genre_ids, haystack)
            score_value -= self._emotion_penalty(parsed_prompt, movie_genre_ids, haystack, primary=primary)
            score_value -= self._narrative_penalty(parsed_prompt, movie_genre_ids, haystack, primary=primary)
            score_value += self._family_score(parsed_prompt, family_defaults, movie_genre_ids, haystack)
            score_value -= self._family_penalty(parsed_prompt, family_defaults, movie_genre_ids, haystack)
            if mode == "similar":
                score_value += self._similarity_score(parsed_prompt, movie_genre_ids, haystack, movie)

            if mode == "person_hidden":
                score_value -= min(popularity / 15.0, 6.0)

            return score_value

        scored_movies = [(movie, score(movie)) for movie in movies]
        scored_movies.sort(key=lambda item: item[1], reverse=True)
        logger.debug(
            "ranking family=%s top_scores=%s",
            parsed_prompt.intent_family,
            [
                (
                    str(movie.get("title") or "Unknown"),
                    round(score_value, 2),
                    self._score_signal_labels(parsed_prompt, self._movie_genre_ids(movie), self._movie_haystack(movie), primary),
                )
                for movie, score_value in scored_movies[:5]
            ],
        )
        return [movie for movie, _ in scored_movies]

    def _genre_names(self, detailed_genres: list[dict] | None, fallback_ids: list[int] | None) -> list[str]:
        if detailed_genres:
            return [genre["name"] for genre in detailed_genres if genre.get("name")]
        if fallback_ids:
            return [TMDB_GENRE_NAMES[genre_id] for genre_id in fallback_ids if genre_id in TMDB_GENRE_NAMES]
        return []

    def _build_reason(
        self,
        prompt: str,
        parsed_prompt: ParsedPrompt,
        genre_names: list[str],
        overview: str,
    ) -> str:
        genre_text = ", ".join(genre_names[:2]).lower() if genre_names else "broad movie"
        signal_parts: list[str] = []
        if parsed_prompt.emotional_targets:
            signal_parts.append(f"emotional targets like {', '.join(parsed_prompt.emotional_targets[:2])}")
        if parsed_prompt.narrative_targets:
            signal_parts.append(f"narrative aims like {', '.join(parsed_prompt.narrative_targets[:2])}")
        elif parsed_prompt.story_outcomes:
            signal_parts.append(f"story outcomes like {', '.join(parsed_prompt.story_outcomes[:2])}")
        if not signal_parts and parsed_prompt.soft_preferences:
            signal_parts.append(f"mood cues like {', '.join(parsed_prompt.soft_preferences[:2])}")
        summary = overview[:160].strip()
        return (
            f'Picked for "{prompt}" because it aligns with your interpreted {genre_text}'
            f'{", " + ", ".join(signal_parts) if signal_parts else ""}. '
            f"{summary}"
        )

    def _extract_hint_query(self, parsed_prompt: ParsedPrompt) -> str:
        parts = [
            *parsed_prompt.soft_preferences[:3],
            *parsed_prompt.themes[:2],
            *parsed_prompt.story_outcomes[:2],
            *parsed_prompt.character_dynamics[:2],
        ]
        return " ".join(parts).strip()

    def _recovery_search_queries(
        self,
        plan: GroupPlan,
        prompt: str,
        parsed_prompt: ParsedPrompt,
    ) -> list[str]:
        queries: list[str] = []
        if parsed_prompt.retrieval_summary:
            queries.append(parsed_prompt.retrieval_summary)
        rewrite = self._normalized_recovery_terms(parsed_prompt)
        if rewrite:
            queries.append(rewrite)
        if plan.query and plan.query not in queries:
            queries.append(plan.query)
        hint_query = self._extract_hint_query(parsed_prompt)
        if hint_query and hint_query not in queries:
            queries.append(hint_query)
        if parsed_prompt.reference_titles:
            for variant in self._reference_resolution_queries(parsed_prompt.reference_titles[0]):
                if variant not in queries:
                    queries.append(variant)
        prompt_text = prompt.strip()
        if prompt_text and prompt_text not in queries:
            queries.append(prompt_text)
        return [query for query in queries if query]

    def _normalized_recovery_terms(self, parsed_prompt: ParsedPrompt) -> str:
        parts: list[str] = []
        if self._healing_prompt(parsed_prompt):
            parts.extend(["emotional healing", "drama", "relationship-centered", "reconciliation", "family"])
        if self._cry_romance_prompt(parsed_prompt):
            parts.extend(["romance", "drama", "heartbreak", "sacrifice", "tragic love"])
        if "warm" in parsed_prompt.tone or "warmer" in parsed_prompt.soft_preferences:
            parts.extend(["warm", "hope", "connection", "human relationships"])
        if "less-dark" in parsed_prompt.soft_preferences or "lighter" in parsed_prompt.soft_preferences:
            parts.extend(["hopeful", "accessible", "thoughtful"])
        if "less-confusing" in parsed_prompt.soft_preferences:
            parts.extend(["accessible", "linear", "thoughtful"])
        parts.extend(parsed_prompt.themes[:3])
        return " ".join(dict.fromkeys(parts))

    def _reference_query(self, parsed_prompt: ParsedPrompt) -> str:
        parts = []
        if parsed_prompt.reference_titles:
            parts.extend(parsed_prompt.reference_titles[:1])
        parts.extend(parsed_prompt.soft_preferences[:2])
        parts.extend(parsed_prompt.themes[:2])
        parts.extend(parsed_prompt.story_outcomes[:1])
        if parsed_prompt.hard_genres:
            parts.append(parsed_prompt.hard_genres[0]["label"])
        return " ".join(parts).strip()

    def _apply_exclusions(self, movies: list[dict], parsed_prompt: ParsedPrompt) -> list[dict]:
        exclusion_terms = [*parsed_prompt.exclude_terms, *parsed_prompt.avoid_elements]
        if not exclusion_terms:
            return movies
        filtered = []
        for movie in movies:
            haystack = " ".join(
                filter(None, [movie.get("title", ""), movie.get("overview", "")])
            ).lower()
            if any(term.lower() in haystack for term in exclusion_terms):
                continue
            filtered.append(movie)
        return filtered

    def _apply_quality_filters(
        self,
        movies: list[dict],
        parsed_prompt: ParsedPrompt,
        strict: bool,
    ) -> list[dict]:
        filtered: list[dict] = []
        for movie in movies:
            movie_genre_ids = self._movie_genre_ids(movie)
            haystack = " ".join(
                filter(None, [movie.get("title", ""), movie.get("overview", "")])
            ).lower()

            if not movie.get("poster_path"):
                continue

            if parsed_prompt.query_type == "general" and not self._is_released_movie(movie):
                continue

            if any(term in haystack for term in SPECIAL_CONTENT_TERMS):
                continue

            if 99 in movie_genre_ids and not self._allows_documentary(parsed_prompt):
                continue

            if 10770 in movie_genre_ids:
                continue

            if strict and int(movie.get("vote_count") or 0) < 50:
                continue

            if strict and not self._allows_animation(parsed_prompt) and 16 in movie_genre_ids:
                continue

            if strict and 10751 in movie_genre_ids and "family" not in haystack and not self._wants_family(parsed_prompt):
                continue

            if strict and 35 in movie_genre_ids and not self._wants_fun(parsed_prompt):
                continue

            filtered.append(movie)
        return filtered

    def _apply_family_filter(
        self,
        movies: list[dict],
        parsed_prompt: ParsedPrompt,
        strict: bool,
    ) -> list[dict]:
        if parsed_prompt.intent_family in {"general", "reference"}:
            return movies

        rules = FAMILY_FILTER_RULES.get(parsed_prompt.intent_family)
        if rules is None:
            return movies

        explicit_required = self._required_genre_ids(parsed_prompt)
        blocked_genres = set(rules["block"]) - explicit_required
        allow_genres = set(rules["allow"]) | set(rules["soft_allow"]) | explicit_required
        filtered: list[dict] = []
        rejected_examples: list[str] = []

        for movie in movies:
            genre_ids = self._movie_genre_ids(movie)
            haystack = " ".join(
                filter(None, [movie.get("title", ""), movie.get("overview", ""), movie.get("tagline", "")])
            ).lower()
            should_reject = False

            if genre_ids & blocked_genres:
                should_reject = True
            if parsed_prompt.intent_family == "sad_emotional" and any(
                term in haystack for term in {"superhero", "franchise", "avengers", "transformers"}
            ):
                should_reject = True
            if parsed_prompt.intent_family == "romance" and any(
                term in haystack for term in {"serial killer", "drug cartel", "battlefield"}
            ):
                should_reject = True
            if parsed_prompt.intent_family == "funny" and any(
                term in haystack for term in {"mourning", "terminal", "grief", "bleak"}
            ):
                should_reject = True
            if strict and parsed_prompt.intent_family == "funny" and "laugh-out-loud" in parsed_prompt.soft_preferences:
                if 35 not in genre_ids:
                    should_reject = True
                if genre_ids & {53, 28}:
                    should_reject = True
            if parsed_prompt.intent_family == "feel_good" and any(
                term in haystack for term in {"tragic", "bleak", "grim", "murder", "killer", "terror", "violent", "despair"}
            ):
                should_reject = True
            if parsed_prompt.intent_family == "dark_intense" and any(
                term in haystack for term in {"family fun", "lighthearted", "playful"}
            ):
                should_reject = True
            if (
                parsed_prompt.intent_family == "narrative"
                and parsed_prompt.ending_type
                and "villain" in parsed_prompt.ending_type.lower()
                and genre_ids & {35, 10751}
            ):
                should_reject = True

            if should_reject and not (genre_ids & explicit_required):
                rejected_examples.append(str(movie.get("title") or "Unknown"))
                continue
            if strict and allow_genres and not (genre_ids & allow_genres):
                rejected_examples.append(str(movie.get("title") or "Unknown"))
                continue
            filtered.append(movie)

        logger.debug(
            "family_filter family=%s filtered_count=%s rejected_examples=%s",
            parsed_prompt.intent_family,
            max(len(movies) - len(filtered), 0),
            rejected_examples[:5],
        )
        return filtered or movies

    def _apply_intent_filters(
        self,
        movies: list[dict],
        parsed_prompt: ParsedPrompt,
        strict: bool,
    ) -> list[dict]:
        required_genre_ids = self._required_genre_ids(parsed_prompt)
        prohibited_genre_ids = self._prohibited_genre_ids(parsed_prompt, strict)
        reference_genre_ids = self._reference_genre_ids(parsed_prompt) if strict else set()

        filtered: list[dict] = []
        for movie in movies:
            movie_genre_ids = self._movie_genre_ids(movie)

            if parsed_prompt.year is not None:
                release_date = movie.get("release_date") or ""
                if not release_date.startswith(str(parsed_prompt.year)):
                    if strict:
                        continue

            if parsed_prompt.wants_animation and 16 not in movie_genre_ids:
                continue

            if parsed_prompt.wants_anime and movie.get("original_language") != "ja":
                continue

            if required_genre_ids:
                if strict:
                    if not required_genre_ids.issubset(movie_genre_ids):
                        continue
                elif not (movie_genre_ids & required_genre_ids):
                    continue

            if prohibited_genre_ids and movie_genre_ids & prohibited_genre_ids:
                continue

            if strict and parsed_prompt.reference_titles and reference_genre_ids:
                if not (movie_genre_ids & reference_genre_ids):
                    continue

            filtered.append(movie)
        return filtered

    def _required_genre_ids(self, parsed_prompt: ParsedPrompt) -> set[int]:
        required = {genre["id"] for genre in parsed_prompt.hard_genres}
        if parsed_prompt.wants_animation or parsed_prompt.wants_anime:
            required.add(16)
        return required

    def _family_primary_genres(self, parsed_prompt: ParsedPrompt) -> set[int]:
        family_genres = set(FAMILY_PRIMARY_GENRES.get(parsed_prompt.intent_family, set()))
        family_genres.update(self._family_defaults(parsed_prompt)["boost_genres"])
        if parsed_prompt.hard_genres:
            family_genres.update(genre["id"] for genre in parsed_prompt.hard_genres)
        return family_genres

    def _enforce_family_coherence(self, movies: list[dict], parsed_prompt: ParsedPrompt) -> list[dict]:
        primary_genres = self._family_primary_genres(parsed_prompt)
        if not primary_genres or len(movies) <= 2:
            return movies

        target_count = min(MAX_MOVIES_PER_GROUP, len(movies))
        required_ratio = 0.75 if parsed_prompt.intent_family in {"funny", "sad_emotional", "romance", "reference"} else 0.67
        required_matches = math.ceil(target_count * required_ratio)
        matched = [movie for movie in movies if self._movie_genre_ids(movie) & primary_genres]
        unmatched = [movie for movie in movies if not (self._movie_genre_ids(movie) & primary_genres)]

        selected = matched[:required_matches]
        remaining_needed = target_count - len(selected)
        if remaining_needed > 0:
            selected.extend(matched[len(selected):len(selected) + remaining_needed])
            remaining_needed = target_count - len(selected)
        if remaining_needed > 0:
            selected.extend(unmatched[:remaining_needed])

        selected_ids = {movie.get("id") for movie in selected}
        tail = [movie for movie in movies if movie.get("id") not in selected_ids]
        return selected + tail

    def _prohibited_genre_ids(self, parsed_prompt: ParsedPrompt, strict: bool) -> set[int]:
        if not strict:
            return set()
        required = self._required_genre_ids(parsed_prompt)
        prohibited: set[int] = set()
        family_defaults = self._family_defaults(parsed_prompt)
        for genre in parsed_prompt.avoid_genres:
            normalized = genre.strip().lower()
            if normalized in GENRE_MAP:
                prohibited.add(GENRE_MAP[normalized]["id"])
            elif normalized in {"science fiction", "sci-fi", "sci fi"}:
                prohibited.add(878)
        prohibited.update(family_defaults["penalty_genres"])
        if parsed_prompt.intent_family == "reference" and self._reference_disallows_animation(parsed_prompt):
            prohibited.update({16, 10751})
        if 878 in required:
            prohibited.update({16, 35, 80})
        if self._prefers_sad_drama(parsed_prompt):
            prohibited.update({16, 27})
            if not self._wants_fun(parsed_prompt):
                prohibited.add(35)
            if 18 not in required and 10749 not in required:
                prohibited.add(28)
        return prohibited - required

    def _movie_genre_ids(self, movie: dict) -> set[int]:
        if movie.get("genre_ids"):
            return set(movie.get("genre_ids") or [])
        details = movie.get("_details") or {}
        return {
            genre.get("id")
            for genre in details.get("genres", [])
            if genre.get("id") is not None
        }

    def _reference_genre_ids(self, parsed_prompt: ParsedPrompt) -> set[int]:
        if not parsed_prompt.reference_titles:
            return set()

        cache_key = ("reference_genres", parsed_prompt.reference_titles[0].lower())
        cached = self._cache_get(cache_key)
        if cached is not None:
            return set(cached.get("genre_ids", []))

        results = self._search_movies(parsed_prompt.reference_titles[0])
        if not results:
            self._cache_set(cache_key, {"genre_ids": []})
            return set()

        genre_ids = list(results[0].get("genre_ids") or [])
        self._cache_set(cache_key, {"genre_ids": genre_ids})
        return set(genre_ids)

    def _family_defaults(self, parsed_prompt: ParsedPrompt) -> dict[str, object]:
        family = parsed_prompt.intent_family
        defaults: dict[str, object] = {
            "default_genre_id": None,
            "must_have_genres": set(),
            "boost_genres": set(),
            "penalty_genres": set(),
            "must_have_signals": [],
            "penalty_signals": [],
        }
        if family == "romance":
            defaults.update(
                {
                    "default_genre_id": 10749,
                    "boost_genres": {10749, 18, 35},
                    "penalty_genres": {28, 27, 80, 878},
                    "must_have_signals": ["relationship", "love", "romance", "connection"],
                    "penalty_signals": ["violence", "crime", "war", "superhero"],
                }
            )
        elif family == "sad_emotional":
            defaults.update(
                {
                    "default_genre_id": 18,
                    "boost_genres": {18, 10749, 10751},
                    "penalty_genres": {28, 35, 27},
                    "must_have_signals": ["grief", "loss", "heartbreak", "family", "tragedy", "healing", "recovery", "reunion", "forgiveness", "relationship"],
                    "penalty_signals": ["superhero", "franchise", "explosion"],
                }
            )
        elif family == "feel_good":
            defaults.update(
                {
                    "default_genre_id": 35,
                    "boost_genres": {35, 10749, 10751, 12, 18},
                    "penalty_genres": {27, 53, 80, 10752, 28},
                    "must_have_signals": ["hope", "friendship", "joy", "warmth", "healing", "kindness", "reunion", "comfort"],
                    "penalty_signals": ["grim", "tragic", "bleak", "murder", "violent", "despair"],
                }
            )
        elif family == "funny":
            defaults.update(
                {
                    "default_genre_id": 35,
                    "boost_genres": {35, 10749, 12},
                    "penalty_genres": {27, 53, 80, 10752, 28},
                    "must_have_signals": ["funny", "laugh", "chaos", "banter", "awkward", "charming", "misadventure"],
                    "penalty_signals": ["grief", "tragic", "bleak", "murder", "war", "trauma"],
                }
            )
        elif family == "dark_intense":
            defaults.update(
                {
                    "default_genre_id": 53,
                    "boost_genres": {53, 9648, 18, 27},
                    "penalty_genres": {35, 10751, 16},
                    "must_have_signals": ["dark", "intense", "obsession", "mystery", "danger"],
                    "penalty_signals": ["playful", "lighthearted", "family"],
                }
            )
        elif family == "reference":
            defaults.update(
                {
                    "default_genre_id": parsed_prompt.hard_genres[0]["id"] if parsed_prompt.hard_genres else None,
                    "must_have_genres": self._reference_genre_ids(parsed_prompt),
                    "boost_genres": self._reference_genre_ids(parsed_prompt),
                    "penalty_signals": ["trending", "generic", "franchise"],
                }
            )
        elif family == "narrative":
            defaults.update(
                {
                    "default_genre_id": parsed_prompt.hard_genres[0]["id"] if parsed_prompt.hard_genres else 18,
                    "boost_genres": {18, 53, 9648},
                    "penalty_genres": {35, 10751},
                    "must_have_signals": parsed_prompt.story_outcomes[:3] + parsed_prompt.character_dynamics[:2],
                }
            )
        elif family == "use_case":
            use_case_default = self._use_case_default_genre(parsed_prompt)
            defaults.update(
                {
                    "default_genre_id": use_case_default,
                    "boost_genres": {use_case_default} if use_case_default is not None else set(),
                    "must_have_signals": parsed_prompt.must_have[:3],
                }
            )
        elif family == "constraint":
            defaults.update(
                {
                    "default_genre_id": parsed_prompt.hard_genres[0]["id"] if parsed_prompt.hard_genres else 18,
                    "boost_genres": {parsed_prompt.hard_genres[0]["id"]} if parsed_prompt.hard_genres else {18},
                    "penalty_signals": parsed_prompt.avoid_elements[:4] + parsed_prompt.avoid_genres[:3],
                }
            )
        elif family == "mixed":
            defaults.update(
                {
                    "default_genre_id": parsed_prompt.hard_genres[0]["id"] if parsed_prompt.hard_genres else self._mixed_default_genre(parsed_prompt),
                    "boost_genres": self._mixed_boost_genres(parsed_prompt),
                    "penalty_genres": self._mixed_penalty_genres(parsed_prompt),
                    "must_have_signals": parsed_prompt.must_have[:4],
                    "penalty_signals": parsed_prompt.avoid_elements[:4],
                }
            )
        return defaults

    def _family_debug_info(self, parsed_prompt: ParsedPrompt) -> dict[str, object]:
        defaults = self._family_defaults(parsed_prompt)
        return {
            "intent_family": parsed_prompt.intent_family,
            "emotional_targets": parsed_prompt.emotional_targets,
            "narrative_targets": parsed_prompt.narrative_targets or parsed_prompt.story_outcomes,
            "must_have_signals": defaults["must_have_signals"],
            "penalty_signals": defaults["penalty_signals"],
            "boost_genres": sorted(defaults["boost_genres"]),
            "penalty_genres": sorted(defaults["penalty_genres"]),
        }

    def _use_case_default_genre(self, parsed_prompt: ParsedPrompt) -> int | None:
        summary = parsed_prompt.retrieval_summary.lower()
        if "date night" in summary:
            return 10749
        if "family night" in summary or parsed_prompt.audience == "family friendly":
            return 16 if parsed_prompt.wants_animation else 10751
        if "late night" in summary:
            return 878
        if "rainy day" in summary:
            return 18
        if any(term in summary for term in ["relaxed night", "comfort", "cozy", "wholesome"]):
            return 35
        return 10749

    def _mixed_default_genre(self, parsed_prompt: ParsedPrompt) -> int | None:
        preferences = set(parsed_prompt.soft_preferences) | set(parsed_prompt.tone)
        if {"funny", "romantic"} & preferences or ("love" in parsed_prompt.retrieval_summary.lower() and "funny" in preferences):
            return 10749
        if self._cry_romance_prompt(parsed_prompt):
            return 10749
        if self._healing_prompt(parsed_prompt):
            return 18
        if {"sad", "emotional"} & preferences:
            return 18
        if {"dark", "darker"} & preferences:
            return 53
        return None

    def _mixed_boost_genres(self, parsed_prompt: ParsedPrompt) -> set[int]:
        genres: set[int] = set()
        summary = parsed_prompt.retrieval_summary.lower()
        preferences = set(parsed_prompt.soft_preferences) | set(parsed_prompt.tone)
        if "love" in summary or "romantic" in preferences:
            genres.update({10749, 18})
        if self._cry_romance_prompt(parsed_prompt):
            genres.update({10749, 18})
        if self._healing_prompt(parsed_prompt):
            genres.update({18, 10749, 10751})
        if {"funny", "fun", "laugh-out-loud", "witty", "banter", "rom-com"} & preferences:
            genres.update({35, 12, 10749})
        if "sad" in preferences or "emotional" in preferences:
            genres.update({18, 10749})
        if "dark" in preferences or "darker" in preferences:
            genres.update({53, 9648})
        return genres

    def _mixed_penalty_genres(self, parsed_prompt: ParsedPrompt) -> set[int]:
        genres: set[int] = set()
        preferences = set(parsed_prompt.soft_preferences) | set(parsed_prompt.tone)
        if "sad" in preferences or "emotional" in preferences:
            genres.update({28, 27})
        if self._cry_romance_prompt(parsed_prompt):
            genres.update({28, 27, 80, 878})
        if self._healing_prompt(parsed_prompt):
            genres.update({28, 27, 80, 53})
        if {"funny", "fun", "laugh-out-loud", "witty", "banter", "rom-com"} & preferences:
            genres.update({27, 53, 80})
        if "romantic" in preferences or "love" in parsed_prompt.retrieval_summary.lower():
            genres.update({27, 80})
        return genres

    def _family_recovery_genre_ids(self, parsed_prompt: ParsedPrompt) -> list[int]:
        if parsed_prompt.intent_family == "reference":
            reference_genres = list(self._reference_genre_ids(parsed_prompt))
            if reference_genres:
                return reference_genres[:3]
        if self._cry_romance_prompt(parsed_prompt):
            return [10749, 18, 10751]
        if self._healing_prompt(parsed_prompt) or self._prefers_sad_drama(parsed_prompt):
            return [18, 10749, 10751]
        family = parsed_prompt.intent_family
        mapping = {
            "romance": [10749, 18, 35],
            "sad_emotional": [18, 10749, 10751],
            "feel_good": [35, 10749, 10751],
            "funny": [35, 10749, 12],
            "dark_intense": [53, 9648, 18],
        }
        if family in mapping:
            return mapping[family]
        if parsed_prompt.hard_genres:
            return [genre["id"] for genre in parsed_prompt.hard_genres[:3]]
        return [18, 10749]

    def _theme_recovery_genre_ids(self, parsed_prompt: ParsedPrompt) -> list[int]:
        genre_ids: list[int] = []
        if any(theme in {"family", "family conflict", "reconciliation", "forgiveness", "recovery"} for theme in parsed_prompt.themes):
            genre_ids.extend([18, 10751, 10749])
        if any(theme in {"love", "memory", "sacrifice"} for theme in parsed_prompt.themes):
            genre_ids.extend([10749, 18, 878])
        if "warm" in parsed_prompt.tone or "warmer" in parsed_prompt.soft_preferences:
            genre_ids.extend([18, 10749])
        if "less-dark" in parsed_prompt.soft_preferences or "lighter" in parsed_prompt.soft_preferences:
            genre_ids.extend([18, 878])
        if parsed_prompt.reference_titles and not genre_ids:
            genre_ids.extend(self._family_recovery_genre_ids(parsed_prompt))
        return list(dict.fromkeys(genre_ids or self._family_recovery_genre_ids(parsed_prompt)))

    def _clean_similar_results(
        self,
        movies: list[dict],
        parsed_prompt: ParsedPrompt,
        strict: bool,
    ) -> list[dict]:
        filtered: list[dict] = []
        reference_genre_ids = self._reference_genre_ids(parsed_prompt)
        require_scifi = 878 in reference_genre_ids and not self._allows_animation(parsed_prompt)

        for movie in movies[:MAX_CANDIDATES]:
            genre_ids = self._movie_genre_ids(movie)
            haystack = " ".join(
                filter(None, [movie.get("title", ""), movie.get("overview", "")])
            ).lower()
            release_year = self._release_year(movie)
            vote_count = int(movie.get("vote_count") or 0)
            vote_average = float(movie.get("vote_average") or 0.0)

            if not movie.get("poster_path"):
                continue
            if vote_count < 200:
                continue
            if vote_average < 6.0:
                continue
            if 10770 in genre_ids:
                continue
            if release_year and release_year < 1980 and parsed_prompt.year is None:
                continue
            if self._reference_disallows_animation(parsed_prompt) and (16 in genre_ids or 10751 in genre_ids):
                continue
            if self._serious_similarity_prompt(parsed_prompt) and 35 in genre_ids and 18 not in genre_ids:
                continue
            if self._thoughtful_similarity_prompt(parsed_prompt) and any(
                term in haystack for term in {"marvel", "avengers", "transformers", "fast & furious", "justice league", "mission impossible"}
            ):
                continue
            if require_scifi and 878 not in genre_ids:
                continue
            if strict and self._is_similarity_outlier(parsed_prompt, genre_ids, haystack):
                continue
            filtered.append(movie)

        if strict and len(filtered) >= 3:
            return filtered
        return [
            movie for movie in filtered
            if not self._is_hard_similarity_mismatch(parsed_prompt, self._movie_genre_ids(movie))
        ]

    def _similarity_score(
        self,
        parsed_prompt: ParsedPrompt,
        movie_genre_ids: set[int],
        haystack: str,
        movie: dict,
    ) -> float:
        score = 0.0
        reference_genre_ids = self._reference_genre_ids(parsed_prompt)
        vote_count = float(movie.get("vote_count") or 0.0)
        vote_average = float(movie.get("vote_average") or 0.0)
        release_year = self._release_year(movie)

        if parsed_prompt.reference_titles:
            score += 5.0 * len(movie_genre_ids & reference_genre_ids)

        if 878 in reference_genre_ids and 878 in movie_genre_ids:
            score += 10.0
            if movie_genre_ids & {18, 9648, 53}:
                score += 6.0
            if 28 in movie_genre_ids and not (movie_genre_ids & {18, 9648, 53}):
                score -= 7.0
            if movie_genre_ids & {27, 35}:
                score -= 8.0
            if not self._allows_animation(parsed_prompt) and 16 in movie_genre_ids:
                score -= 10.0
            if 10751 in movie_genre_ids:
                score -= 6.0
            if 35 in movie_genre_ids and 18 not in movie_genre_ids:
                score -= 7.0
            if any(term in haystack for term in {"marvel", "avengers", "transformers", "justice league", "franchise"}):
                score -= 8.0

        score += min(vote_count / 120.0, 24.0)
        score += vote_average * 2.5
        if release_year:
            score += max(min((release_year - 1990) / 6.0, 5.0), 0.0)

        if "warmer" in parsed_prompt.soft_preferences:
            if movie_genre_ids & {18, 10749}:
                score += 8.0
            if any(term in haystack for term in {"hope", "hopeful", "family", "relationship", "connection", "humanity", "love", "healing", "reunion"}):
                score += 6.0
            if any(term in haystack for term in {"cold", "detached", "bleak", "grim"}):
                score -= 8.0
        if any(term in parsed_prompt.soft_preferences for term in {"less-dark", "lighter", "more-hopeful"}):
            if movie_genre_ids & {18, 10749, 12}:
                score += 4.0
            if any(term in haystack for term in {"hope", "hopeful", "healing", "friendship", "reunion", "support"}):
                score += 4.0
            if any(term in haystack for term in {"grim", "bleak", "cold", "doomed"}):
                score -= 5.0
        if "darker" in parsed_prompt.soft_preferences and movie_genre_ids & {53, 9648}:
            score += 7.0
        if "darker" in parsed_prompt.soft_preferences and any(term in haystack for term in {"tragedy", "doom", "villain", "obsession", "collapse", "corruption"}):
            score += 5.0
        if "darker" in parsed_prompt.soft_preferences and any(term in haystack for term in {"lighthearted", "playful", "family fun", "silly"}):
            score -= 7.0
        if "more-emotional" in parsed_prompt.soft_preferences:
            if movie_genre_ids & {18, 10749}:
                score += 5.0
            if any(term in haystack for term in {"family", "love", "grief", "connection", "memory", "heart"}):
                score += 4.0
        if "funnier" in parsed_prompt.soft_preferences:
            if movie_genre_ids & {35, 10749, 12}:
                score += 4.5
            if any(term in haystack for term in {"banter", "funny", "laugh", "charming", "awkward"}):
                score += 4.0
        if "less-confusing" in parsed_prompt.soft_preferences:
            if movie_genre_ids & {9648}:
                score -= 5.0
            if any(term in haystack for term in {"dream", "paradox", "abstract", "nonlinear", "fractured", "labyrinth", "metaphysical"}):
                score -= 6.0
        if any(term in haystack for term in {"space", "mission", "humanity", "isolation", "future", "planet", "alien"}):
            score += 2.0
        if movie_genre_ids & {18} and 878 in movie_genre_ids:
            score += 3.0
        if any(term in haystack for term in {"father", "daughter", "family", "memory", "connection", "human"}):
            score += 2.5
        if self._reference_disallows_animation(parsed_prompt) and (16 in movie_genre_ids or 10751 in movie_genre_ids):
            score -= 12.0
        if self._reference_is_prestige_scifi(parsed_prompt) and movie_genre_ids & {35, 10751}:
            score -= 8.0
        if self._reference_is_blockbuster(parsed_prompt) and any(term in haystack for term in {"playful", "family fun", "kids"}):
            score -= 6.0

        return score

    def _is_similarity_outlier(
        self,
        parsed_prompt: ParsedPrompt,
        movie_genre_ids: set[int],
        haystack: str,
    ) -> bool:
        reference_genre_ids = self._reference_genre_ids(parsed_prompt)
        if 878 in reference_genre_ids and 878 not in movie_genre_ids:
            return True
        if 878 in reference_genre_ids and movie_genre_ids & {27, 35}:
            return True
        if any(term in haystack for term in {"shark", "zombie", "post-apocalyptic", "wasteland", "raider", "monster attack", "transformers"}):
            return True
        if self._reference_disallows_animation(parsed_prompt) and (16 in movie_genre_ids or 10751 in movie_genre_ids):
            return True
        return False

    def _is_hard_similarity_mismatch(self, parsed_prompt: ParsedPrompt, movie_genre_ids: set[int]) -> bool:
        reference_genre_ids = self._reference_genre_ids(parsed_prompt)
        if 878 in reference_genre_ids and 878 not in movie_genre_ids:
            return True
        if self._reference_disallows_animation(parsed_prompt) and (16 in movie_genre_ids or 10751 in movie_genre_ids):
            return True
        if movie_genre_ids & {27, 10770}:
            return True
        if self._serious_similarity_prompt(parsed_prompt) and 35 in movie_genre_ids and 18 not in movie_genre_ids:
            return True
        return False

    def _secondary_genre_match_count(self, movie_genre_ids: set[int], parsed_prompt: ParsedPrompt) -> int:
        desired: set[int] = set()
        if "emotional" in parsed_prompt.soft_preferences:
            desired.update({18, 10749, 878})
        if self._prefers_sad_drama(parsed_prompt):
            desired.update({18, 10749, 10751})
        if any(item in {"romantic", "warm", "cozy"} for item in parsed_prompt.tone):
            desired.update({10749, 18, 10751})
        if any(item in {"family", "love", "memory"} for item in parsed_prompt.themes):
            desired.update({18, 10749, 10751})
        if "dark" in parsed_prompt.soft_preferences:
            desired.update({53, 9648, 18})
        if "fun" in parsed_prompt.soft_preferences or "funny" in parsed_prompt.soft_preferences:
            desired.update({35, 12, 10751})
        if "cozy" in parsed_prompt.soft_preferences:
            desired.update({10749, 35, 10751})
        if "stylish" in parsed_prompt.soft_preferences or "mind-bending" in parsed_prompt.soft_preferences:
            desired.update({18, 53, 9648, 878})
        return len(movie_genre_ids & desired)

    def _family_score(
        self,
        parsed_prompt: ParsedPrompt,
        family_defaults: dict[str, object],
        movie_genre_ids: set[int],
        haystack: str,
    ) -> float:
        score = 0.0
        boost_genres = family_defaults["boost_genres"]
        must_have_genres = family_defaults["must_have_genres"]
        must_have_signals = family_defaults["must_have_signals"]

        if boost_genres:
            score += 3.0 * len(movie_genre_ids & boost_genres)
        if must_have_genres:
            score += 4.0 * len(movie_genre_ids & must_have_genres)
            if parsed_prompt.intent_family == "reference" and not (movie_genre_ids & must_have_genres):
                score -= 12.0
        primary_genres = self._family_primary_genres(parsed_prompt)
        if primary_genres and movie_genre_ids & primary_genres:
            score += 3.0
        score += 1.5 * sum(1 for signal in must_have_signals if signal.lower() in haystack)

        if parsed_prompt.intent_family == "use_case":
            summary = parsed_prompt.retrieval_summary.lower()
            if "date night" in summary and movie_genre_ids & {10749, 35}:
                score += 6.0
            if "family night" in summary and movie_genre_ids & {10751, 16}:
                score += 6.0
            if "late night" in summary and movie_genre_ids & {878, 9648, 18}:
                score += 5.0
            if "rainy day" in summary and movie_genre_ids & {18, 10749}:
                score += 5.0
        if parsed_prompt.intent_family == "narrative":
            if parsed_prompt.ending_type and parsed_prompt.ending_type.lower() in haystack:
                score += 5.0
            if any(signal.lower() in haystack for signal in parsed_prompt.story_outcomes):
                score += 4.0
            if "villain" in (parsed_prompt.ending_type or "").lower() and movie_genre_ids & {53, 18, 9648}:
                score += 4.0
        return score

    def _family_penalty(
        self,
        parsed_prompt: ParsedPrompt,
        family_defaults: dict[str, object],
        movie_genre_ids: set[int],
        haystack: str,
    ) -> float:
        penalty = 0.0
        penalty_genres = family_defaults["penalty_genres"]
        penalty_signals = family_defaults["penalty_signals"]
        if penalty_genres:
            penalty += 3.5 * len(movie_genre_ids & penalty_genres)
        penalty += 1.75 * sum(1 for signal in penalty_signals if signal.lower() in haystack)

        primary_genres = self._family_primary_genres(parsed_prompt)
        if primary_genres and not (movie_genre_ids & primary_genres):
            penalty += 3.0

        if parsed_prompt.intent_family == "reference":
            if any(term in haystack for term in {"trending", "generic"}):
                penalty += 4.0
            if "warmer" in parsed_prompt.soft_preferences and any(term in haystack for term in {"cold", "detached", "bleak", "grim"}):
                penalty += 6.0
            if "darker" in parsed_prompt.soft_preferences and any(term in haystack for term in {"lighthearted", "playful", "family fun", "silly"}):
                penalty += 6.0
        if parsed_prompt.intent_family == "funny" and any(term in haystack for term in {"grief", "mourning", "bleak", "terminal"}):
            penalty += 5.0
        if parsed_prompt.intent_family == "funny" and any(term in haystack for term in {"murder", "terror", "killer", "corruption", "war", "brutality"}):
            penalty += 6.0
        if parsed_prompt.intent_family == "funny" and "laugh-out-loud" in parsed_prompt.soft_preferences:
            if 35 not in movie_genre_ids:
                penalty += 8.0
            if movie_genre_ids & {18, 53, 28} and 35 not in movie_genre_ids:
                penalty += 6.0
        if parsed_prompt.intent_family == "romance" and any(term in haystack for term in {"serial killer", "criminal empire", "war zone"}):
            penalty += 6.0
        if parsed_prompt.intent_family == "sad_emotional" and any(term in haystack for term in {"superhero", "franchise", "explosive", "mission"}):
            penalty += 6.0
        if parsed_prompt.intent_family == "sad_emotional" and movie_genre_ids & {28, 878, 53, 27}:
            penalty += 4.0
        if parsed_prompt.intent_family == "romance" and movie_genre_ids & {27, 80, 10752, 28}:
            penalty += 4.0
        if parsed_prompt.intent_family == "funny" and movie_genre_ids & {27, 53, 18, 80, 10752}:
            penalty += 3.8
        if parsed_prompt.intent_family == "feel_good" and movie_genre_ids & {27, 53}:
            penalty += 4.0
        if parsed_prompt.intent_family == "dark_intense" and movie_genre_ids & {35, 10751}:
            penalty += 4.0
        if parsed_prompt.intent_family == "dark_intense" and any(term in haystack for term in {"playful", "whimsical", "family fun"}):
            penalty += 6.0
        return penalty

    def _movie_haystack(self, movie: dict) -> str:
        details = movie.get("_details") or {}
        return " ".join(
            filter(
                None,
                [
                    movie.get("title", ""),
                    details.get("title", ""),
                    movie.get("overview", ""),
                    details.get("overview", ""),
                    details.get("tagline", ""),
                ],
            )
        ).lower()

    def _emotion_targets(self, parsed_prompt: ParsedPrompt) -> list[str]:
        targets = [*parsed_prompt.emotional_targets, *parsed_prompt.soft_preferences, *parsed_prompt.tone]
        if parsed_prompt.intent_family == "sad_emotional":
            targets.extend(["sad", "emotional"])
        if parsed_prompt.intent_family == "feel_good":
            targets.extend(["warm", "uplifting", "cozy", "comfort", "wholesome"])
        if parsed_prompt.intent_family == "romance":
            targets.append("emotional")
        if parsed_prompt.intent_family == "funny":
            targets.extend(["funny"])
        if self._healing_prompt(parsed_prompt):
            targets.extend(["emotional healing", "healing", "cathartic"])
        if self._cry_romance_prompt(parsed_prompt):
            targets.extend(["heartbreaking", "cry-worthy", "sad"])
        return _normalize_text_list(targets)

    def _narrative_targets(self, parsed_prompt: ParsedPrompt) -> list[str]:
        targets = [*parsed_prompt.narrative_targets, *parsed_prompt.story_outcomes]
        if parsed_prompt.ending_type:
            targets.append(parsed_prompt.ending_type)
        return _normalize_text_list(targets)

    def _emotion_score(
        self,
        parsed_prompt: ParsedPrompt,
        movie_genre_ids: set[int],
        haystack: str,
        *,
        primary: bool,
    ) -> float:
        targets = self._emotion_targets(parsed_prompt)
        if not targets:
            return 0.0

        score = 0.0
        weight = 1.5 if primary else 0.75
        if primary and (self._healing_prompt(parsed_prompt) or self._cry_romance_prompt(parsed_prompt)):
            weight *= 1.35
        if {"sad", "emotional", "heartbreaking", "tragic"} & set(targets):
            if movie_genre_ids & {18, 10749}:
                score += 5.0 * weight
            if 10751 in movie_genre_ids and 35 not in movie_genre_ids:
                score += 2.5 * weight
            if any(target in {"sad", "heartbreaking", "tragic"} for target in targets):
                score += weight * sum(
                    1.1 for term in EMOTION_SIGNAL_KEYWORDS["sad"] | EMOTION_SIGNAL_KEYWORDS["heartbreaking"] if term in haystack
                )
        if {"warm", "uplifting", "emotional healing"} & set(targets):
            if movie_genre_ids & {18, 10749, 10751, 35}:
                score += 3.5 * weight
                for target in {"warm", "uplifting", "emotional healing"} & set(targets):
                    score += weight * sum(1.0 for term in EMOTION_SIGNAL_KEYWORDS[target] if term in haystack)
        if self._healing_prompt(parsed_prompt):
            if movie_genre_ids & {18, 10749, 10751}:
                score += 5.0 * weight
            score += weight * sum(1.2 for term in HEALING_POSITIVE_SIGNALS if term in haystack)
        if self._cry_romance_prompt(parsed_prompt):
            if movie_genre_ids & {18, 10749} == {18, 10749}:
                score += 5.5 * weight
            elif movie_genre_ids & {18, 10749}:
                score += 3.5 * weight
            score += weight * sum(
                1.1
                for term in {
                    "heartbreak",
                    "separation",
                    "sacrifice",
                    "tragic",
                    "relationship",
                    "love",
                    "loss",
                    "reunion",
                }
                if term in haystack
            )
        if {"cozy", "comfort", "wholesome", "relaxing", "easy watch"} & set(targets):
            if movie_genre_ids & {35, 10749, 10751, 12}:
                score += 4.0 * weight
            if 18 in movie_genre_ids and not (movie_genre_ids & {27, 53, 80}):
                score += 2.0 * weight
            for target in {"cozy", "comfort", "wholesome", "relaxing", "easy watch"} & set(targets):
                score += weight * sum(1.0 for term in EMOTION_SIGNAL_KEYWORDS[target] if term in haystack)
        if parsed_prompt.intent_family == "feel_good":
            if movie_genre_ids & {35, 10749, 10751, 12}:
                score += 4.5 * weight
            if 18 in movie_genre_ids and not (movie_genre_ids & {27, 53, 80, 10752, 28}):
                score += 2.5 * weight
            score += weight * sum(0.9 for term in FEEL_GOOD_POSITIVE_SIGNALS if term in haystack)
            if parsed_prompt.complexity in {"easy watch"} or "easy-watch" in parsed_prompt.soft_preferences:
                if not movie_genre_ids & {53, 9648, 27}:
                    score += 2.5 * weight
            if parsed_prompt.pacing in {"fast paced", "dialogue-heavy"}:
                score += 0.5 * weight
        if "bittersweet" in targets:
            if movie_genre_ids & {18, 10749}:
                score += 3.5 * weight
            score += weight * sum(1.0 for term in EMOTION_SIGNAL_KEYWORDS["bittersweet"] if term in haystack)
        if parsed_prompt.intent_family == "funny":
            funny_preferences = set(parsed_prompt.soft_preferences) | set(parsed_prompt.tone)
            if movie_genre_ids & {35, 10749, 12}:
                score += 4.5 * weight
            score += weight * sum(0.9 for term in FUNNY_POSITIVE_SIGNALS if term in haystack)
            if "laugh-out-loud" in funny_preferences:
                if 35 in movie_genre_ids:
                    score += 7.0 * weight
                if movie_genre_ids & {12}:
                    score += 1.5 * weight
                score += weight * sum(1.3 for term in {"hilarious", "laugh", "chaotic", "awkward", "absurd", "ridiculous", "outrageous"} if term in haystack)
            if {"witty", "banter"} & funny_preferences:
                if movie_genre_ids & {35, 10749}:
                    score += 4.0 * weight
                score += weight * sum(1.0 for term in {"banter", "witty", "charming", "rivalry", "odd couple"} if term in haystack)
            if "rom-com" in funny_preferences or ("romantic" in funny_preferences and "funny" in funny_preferences):
                if movie_genre_ids & {35, 10749}:
                    score += 5.0 * weight
                score += weight * sum(1.0 for term in {"date", "wedding", "relationship", "couple", "chemistry"} if term in haystack)
            if "fun" in funny_preferences or "funny" in funny_preferences:
                if movie_genre_ids & {35, 12, 10751}:
                    score += 3.0 * weight
        if parsed_prompt.intent_family == "romance":
            score += weight * sum(1.1 for term in ROMANCE_SIGNAL_KEYWORDS if term in haystack)
        return score

    def _emotion_penalty(
        self,
        parsed_prompt: ParsedPrompt,
        movie_genre_ids: set[int],
        haystack: str,
        *,
        primary: bool,
    ) -> float:
        targets = self._emotion_targets(parsed_prompt)
        if not targets:
            return 0.0

        penalty = 0.0
        weight = 1.4 if primary else 0.7
        if primary and (self._healing_prompt(parsed_prompt) or self._cry_romance_prompt(parsed_prompt)):
            weight *= 1.3
        if {"sad", "emotional", "heartbreaking", "tragic"} & set(targets):
            if movie_genre_ids & {28, 16, 27}:
                penalty += 3.0 * weight
            if 35 in movie_genre_ids and 18 not in movie_genre_ids:
                penalty += 2.5 * weight
            penalty += weight * sum(1.4 for term in BLOCKBUSTER_SPECTACLE_SIGNALS if term in haystack)
        if {"warm", "uplifting", "emotional healing"} & set(targets):
            if any(term in haystack for term in {"cold", "detached", "harsh", "bleak", "grim"}):
                penalty += 2.5 * weight
        if self._healing_prompt(parsed_prompt):
            if movie_genre_ids & {28, 53, 80, 27}:
                penalty += 3.5 * weight
            penalty += weight * sum(1.15 for term in HEALING_NEGATIVE_SIGNALS if term in haystack)
            if any(term in haystack for term in {"brutal", "grim", "terror", "killer", "violent"}):
                penalty += 2.3 * weight
        if self._cry_romance_prompt(parsed_prompt):
            if movie_genre_ids & {28, 80, 27}:
                penalty += 3.8 * weight
            if 878 in movie_genre_ids and not (movie_genre_ids & {18, 10749}):
                penalty += 3.2 * weight
            if any(term in haystack for term in {"murder", "crime", "terror", "killer", "war"}):
                penalty += 2.4 * weight
        if {"cozy", "comfort", "wholesome", "relaxing", "easy watch"} & set(targets):
            if movie_genre_ids & {27, 53, 80}:
                penalty += 3.0 * weight
            if any(term in haystack for term in {"grim", "brutal", "violent", "cold", "harsh"}):
                penalty += 2.8 * weight
        if parsed_prompt.intent_family == "feel_good":
            if movie_genre_ids & {27, 53, 80, 10752}:
                penalty += 3.5 * weight
            if 28 in movie_genre_ids and 35 not in movie_genre_ids and 10749 not in movie_genre_ids:
                penalty += 2.8 * weight
            if movie_genre_ids & {9648} and parsed_prompt.complexity in {"easy watch"}:
                penalty += 2.0 * weight
            penalty += weight * sum(1.25 for term in {"tragic", "doom", "mourning", "terminal"} if term in haystack)
            penalty += weight * sum(1.0 for term in FEEL_GOOD_NEGATIVE_SIGNALS if term in haystack)
        if parsed_prompt.intent_family == "funny":
            funny_preferences = set(parsed_prompt.soft_preferences) | set(parsed_prompt.tone)
            if movie_genre_ids & {27, 53, 80, 10752}:
                penalty += 3.8 * weight
            if 28 in movie_genre_ids and not (movie_genre_ids & {35, 10749, 12}):
                penalty += 3.0 * weight
            if 18 in movie_genre_ids and 35 not in movie_genre_ids and 10749 not in movie_genre_ids:
                penalty += 2.8 * weight
            penalty += weight * sum(1.0 for term in FUNNY_NEGATIVE_SIGNALS if term in haystack)
            if {"witty", "banter", "rom-com"} & funny_preferences and movie_genre_ids & {53, 80, 878}:
                penalty += 2.5 * weight
            if "laugh-out-loud" in funny_preferences:
                if 35 not in movie_genre_ids:
                    penalty += 7.0 * weight
                if movie_genre_ids & {18, 53, 28} and 35 not in movie_genre_ids:
                    penalty += 5.0 * weight
        if parsed_prompt.intent_family == "romance" and movie_genre_ids & {80, 28} and 10749 not in movie_genre_ids:
            penalty += 2.8 * weight
        return penalty

    def _narrative_score(
        self,
        parsed_prompt: ParsedPrompt,
        movie_genre_ids: set[int],
        haystack: str,
        *,
        primary: bool,
    ) -> float:
        targets = self._narrative_targets(parsed_prompt)
        if not targets:
            return 0.0

        score = 0.0
        weight = 1.6 if primary else 0.8
        if primary and (self._healing_prompt(parsed_prompt) or self._cry_romance_prompt(parsed_prompt)):
            weight *= 1.45
        for target in targets:
            if target in NARRATIVE_SIGNAL_KEYWORDS:
                score += weight * sum(1.1 for term in NARRATIVE_SIGNAL_KEYWORDS[target] if term in haystack)
        if "villain wins" in targets and movie_genre_ids & {53, 18, 9648}:
            score += 5.0 * weight
        if {"tragic ending", "bittersweet ending"} & set(targets) and movie_genre_ids & {18, 10749}:
            score += 3.5 * weight
        if "happy ending" in targets and movie_genre_ids & {35, 10749, 10751}:
            score += 3.0 * weight
        if "revenge" in targets and movie_genre_ids & {53, 18, 28}:
            score += 3.0 * weight
        if "redemption" in targets and movie_genre_ids & {18, 10749}:
            score += 3.0 * weight
        if self._healing_prompt(parsed_prompt):
            if movie_genre_ids & {18, 10749, 10751}:
                score += 3.8 * weight
            score += weight * sum(
                1.0
                for term in {
                    "family",
                    "relationship",
                    "mother",
                    "father",
                    "daughter",
                    "son",
                    "reconciliation",
                    "forgiveness",
                    "reunion",
                    "recovery",
                    "second chance",
                }
                if term in haystack
            )
        if self._cry_romance_prompt(parsed_prompt):
            if movie_genre_ids & {18, 10749}:
                score += 4.0 * weight
            score += weight * sum(
                1.0
                for term in {
                    "love",
                    "relationship",
                    "heartbreak",
                    "separation",
                    "sacrifice",
                    "tragic",
                    "loss",
                    "memory",
                }
                if term in haystack
            )
        return score

    def _narrative_penalty(
        self,
        parsed_prompt: ParsedPrompt,
        movie_genre_ids: set[int],
        haystack: str,
        *,
        primary: bool,
    ) -> float:
        targets = self._narrative_targets(parsed_prompt)
        if not targets:
            return 0.0

        penalty = 0.0
        weight = 1.5 if primary else 0.75
        if "villain wins" in targets:
            if movie_genre_ids & {35, 10751}:
                penalty += 4.0 * weight
            if any(term in haystack for term in {"playful", "cheerful", "uplifting", "family fun"}):
                penalty += 3.5 * weight
        if "happy ending" in targets and any(term in haystack for term in {"tragic", "doom", "final loss", "death"}):
            penalty += 3.0 * weight
        if "bittersweet ending" in targets and any(term in haystack for term in {"superhero", "explosive", "franchise"}):
            penalty += 2.5 * weight
        if "less confusing" in parsed_prompt.complexity.lower() if parsed_prompt.complexity else False:
            penalty += weight * sum(1.2 for term in ABSTRACT_COMPLEXITY_SIGNALS if term in haystack)
        if self._healing_prompt(parsed_prompt) and any(
            term in haystack for term in {"flat", "detached", "cold", "brutal", "killer", "terror", "violent"}
        ):
            penalty += 2.4 * weight
        if self._cry_romance_prompt(parsed_prompt) and any(
            term in haystack for term in {"heist", "mission", "crime", "killer", "battlefield", "war"}
        ):
            penalty += 2.6 * weight
        if primary and (self._healing_prompt(parsed_prompt) or self._cry_romance_prompt(parsed_prompt)):
            if movie_genre_ids & {28, 80} and not (movie_genre_ids & {18, 10749}):
                penalty += 4.5 * weight
        return penalty

    def _score_signal_labels(
        self,
        parsed_prompt: ParsedPrompt,
        movie_genre_ids: set[int],
        haystack: str,
        primary: bool,
    ) -> list[str]:
        labels: list[str] = []
        emotion_targets = self._emotion_targets(parsed_prompt)
        narrative_targets = self._narrative_targets(parsed_prompt)
        if emotion_targets:
            labels.append(f"emotion={','.join(emotion_targets[:3])}")
        if narrative_targets:
            labels.append(f"narrative={','.join(narrative_targets[:3])}")
        if primary and movie_genre_ids & self._family_primary_genres(parsed_prompt):
            labels.append("family-genre-match")
        if any(term in haystack for term in BLOCKBUSTER_SPECTACLE_SIGNALS):
            labels.append("spectacle-penalty")
        if any(term in haystack for term in ABSTRACT_COMPLEXITY_SIGNALS):
            labels.append("complexity-penalty")
        return labels[:4]

    def _mood_score(self, parsed_prompt: ParsedPrompt, movie_genre_ids: set[int], haystack: str) -> float:
        score = 0.0
        preferences = set(parsed_prompt.soft_preferences)
        if "emotional" in preferences:
            if movie_genre_ids & {18, 10749}:
                score += 6.0
            if 878 in movie_genre_ids and movie_genre_ids & {18, 9648, 53}:
                score += 4.0
            score += 1.2 * sum(1 for term in EMOTIONAL_TEXT_SIGNALS if term in haystack)
        if self._prefers_sad_drama(parsed_prompt):
            if movie_genre_ids & {18, 10749}:
                score += 8.0
            if 10751 in movie_genre_ids and 35 not in movie_genre_ids:
                score += 4.0
            score += 1.5 * sum(1 for term in SAD_TEXT_SIGNALS if term in haystack)
            if movie_genre_ids & {28, 27, 16}:
                score -= 7.0
            if any(term in haystack for term in {"marvel", "avengers", "transformers", "mission impossible", "fast & furious", "superhero"}):
                score -= 8.0
        if "stylish" in preferences:
            if movie_genre_ids & {18, 53, 9648, 878}:
                score += 5.0
            if float("marvel" in haystack or "avengers" in haystack or "superhero" in haystack):
                score -= 3.5
        if ("dark" in preferences or "darker" in preferences) and movie_genre_ids & {53, 9648, 18}:
            score += 5.0
        if "warmer" in preferences:
            if movie_genre_ids & {18, 10749}:
                score += 7.0
            if any(term in haystack for term in {"hope", "hopeful", "connection", "healing", "love", "tender", "human", "relationship", "family"}):
                score += 5.0
            if any(term in haystack for term in {"cold", "detached", "bleak", "grim"}):
                score -= 6.0
        if {"fun", "funny", "laugh-out-loud"} & preferences:
            if movie_genre_ids & {35, 12, 10751}:
                score += 5.0
            score += 1.0 * sum(1 for term in {"funny", "laugh", "banter", "charming", "chaotic", "absurd"} if term in haystack)
        if {"witty", "banter"} & preferences:
            if movie_genre_ids & {35, 10749}:
                score += 4.5
            score += 1.0 * sum(1 for term in {"banter", "witty", "odd couple", "rivalry"} if term in haystack)
        if "rom-com" in preferences:
            if movie_genre_ids & {35, 10749}:
                score += 5.0
            if movie_genre_ids & {53, 80, 878} and 10749 not in movie_genre_ids:
                score -= 4.0
        if "cozy" in preferences and movie_genre_ids & {10749, 35, 10751}:
            score += 5.0
        if "mind-bending" in preferences:
            if movie_genre_ids & {878, 9648, 53}:
                score += 5.0
            score += 1.0 * sum(1 for term in THOUGHTFUL_SCIFI_TEXT_SIGNALS if term in haystack)
        if "less-confusing" in preferences:
            if movie_genre_ids & {9648, 53}:
                score -= 2.5
            if any(term in haystack for term in {"dream", "paradox", "labyrinth", "fractured", "timeline", "multiverse"}):
                score -= 4.0
        return score

    def _scifi_quality_score(self, parsed_prompt: ParsedPrompt, movie_genre_ids: set[int], haystack: str) -> float:
        required = self._required_genre_ids(parsed_prompt)
        if 878 not in required or parsed_prompt.wants_animation:
            return 0.0
        score = 0.0
        if movie_genre_ids & {18, 53, 9648}:
            score += 6.0
        if 28 in movie_genre_ids and not (movie_genre_ids & {18, 53, 9648}):
            score -= 4.0
        if 10751 in movie_genre_ids:
            score -= 5.0
        if any(term in haystack for term in {"marvel", "avengers", "justice league", "guardians", "x-men"}):
            score -= 5.0
        score += 1.0 * sum(1 for term in THOUGHTFUL_SCIFI_TEXT_SIGNALS if term in haystack)
        return score

    def _generic_penalty(self, parsed_prompt: ParsedPrompt, movie_genre_ids: set[int], haystack: str) -> float:
        penalty = 0.0
        if not self._allows_animation(parsed_prompt) and 16 in movie_genre_ids:
            penalty -= 8.0
        if not self._wants_family(parsed_prompt) and 10751 in movie_genre_ids:
            penalty -= 5.0
        if not self._wants_fun(parsed_prompt) and 35 in movie_genre_ids:
            penalty -= 3.0
        if self._prefers_sad_drama(parsed_prompt):
            if 16 in movie_genre_ids:
                penalty -= 10.0
            if 35 in movie_genre_ids and 18 not in movie_genre_ids:
                penalty -= 8.0
            if 28 in movie_genre_ids and 18 not in movie_genre_ids:
                penalty -= 7.0
            if 27 in movie_genre_ids:
                penalty -= 10.0
            if any(term in haystack for term in {"marvel", "avengers", "transformers", "justice league", "franchise", "superhero"}):
                penalty -= 9.0
        if 10770 in movie_genre_ids:
            penalty -= 8.0
        if 99 in movie_genre_ids and not self._allows_documentary(parsed_prompt):
            penalty -= 8.0
        if any(term in haystack for term in SPECIAL_CONTENT_TERMS):
            penalty -= 8.0
        return penalty

    def _release_year(self, movie: dict) -> int | None:
        release_date = movie.get("release_date") or ""
        if len(release_date) >= 4 and release_date[:4].isdigit():
            return int(release_date[:4])
        return None

    def _embedding_rerank(
        self,
        movies: list[dict],
        prompt: str,
        parsed_prompt: ParsedPrompt,
        plan: GroupPlan,
    ) -> list[dict]:
        if not self._should_use_embedding_rerank(parsed_prompt, plan):
            return movies

        candidates = movies[: min(len(movies), MAX_EMBEDDING_CANDIDATES)]
        if not candidates:
            return movies

        prompt_embedding = self.embedding_service.get_embedding(
            self._prompt_embedding_text(prompt, parsed_prompt)
        )
        if prompt_embedding is None:
            return movies

        movie_texts = [self._movie_embedding_text(movie) for movie in candidates]
        embedding_map = self.embedding_service.get_embeddings(movie_texts)
        if not embedding_map:
            return movies

        base_rank_bonus = {
            movie["id"]: max(len(candidates) - index, 1) * 1.2
            for index, movie in enumerate(candidates)
            if movie.get("id") is not None
        }

        def score(movie: dict) -> float:
            text = self._movie_embedding_text(movie)
            movie_embedding = embedding_map.get(text)
            if movie_embedding is None:
                return float("-inf")

            similarity = self.embedding_service.cosine_similarity(prompt_embedding, movie_embedding)
            vote_count = min(float(movie.get("vote_count") or 0.0) / 250.0, 20.0)
            rating = float(movie.get("vote_average") or 0.0) * 2.0
            heuristic = base_rank_bonus.get(movie.get("id"), 0.0)
        return similarity * 100.0 + vote_count + rating + heuristic

        reranked = sorted(candidates, key=score, reverse=True)
        reranked_ids = {movie["id"] for movie in reranked}
        tail = [movie for movie in movies if movie.get("id") not in reranked_ids]
        return reranked + tail

    def _should_use_embedding_rerank(self, parsed_prompt: ParsedPrompt, plan: GroupPlan) -> bool:
        if plan.key != "best-match":
            return False
        if parsed_prompt.reference_titles:
            return True
        if parsed_prompt.person_name:
            return False
        if parsed_prompt.query_type in {"narrative", "mixed_constraints", "mood"}:
            return True
        if len(parsed_prompt.soft_preferences) >= 2:
            return True
        if parsed_prompt.query_type == "general" and (
            parsed_prompt.hard_genres or parsed_prompt.soft_preferences
        ):
            return True
        return False

    def _movie_embedding_text(self, movie: dict) -> str:
        details = movie.get("_details") or {}
        genres = self._genre_names(details.get("genres"), movie.get("genre_ids"))
        title = movie.get("title") or details.get("title") or ""
        tagline = details.get("tagline") or ""
        overview = movie.get("overview") or details.get("overview") or ""
        genre_text = ", ".join(genres)
        return (
            f"{title}. "
            f"Genres: {genre_text}. "
            f"Tagline: {tagline}. "
            f"Overview: {overview}"
        ).strip()

    def _prompt_embedding_text(self, prompt: str, parsed_prompt: ParsedPrompt) -> str:
        parts = [prompt.strip()]
        intent_summary: list[str] = []
        if parsed_prompt.intent_family != "general":
            intent_summary.append(f"Intent family: {parsed_prompt.intent_family}.")
        if parsed_prompt.reference_titles:
            intent_summary.append(f"Reference titles: {', '.join(parsed_prompt.reference_titles[:2])}.")
        if parsed_prompt.subgenres:
            intent_summary.append(f"Subgenres: {', '.join(parsed_prompt.subgenres[:2])}.")
        if parsed_prompt.hard_genres:
            intent_summary.append(
                "Required genres: "
                + ", ".join(genre["label"] for genre in parsed_prompt.hard_genres[:3])
                + "."
            )
        if parsed_prompt.tone:
            intent_summary.append("Tone: " + ", ".join(parsed_prompt.tone[:3]) + ".")
        if parsed_prompt.soft_preferences:
            intent_summary.append(
                "Tone and preferences: " + ", ".join(parsed_prompt.soft_preferences[:4]) + "."
            )
        if parsed_prompt.emotional_targets:
            intent_summary.append(
                "Emotional targets: " + ", ".join(parsed_prompt.emotional_targets[:4]) + "."
            )
        if parsed_prompt.themes:
            intent_summary.append("Themes: " + ", ".join(parsed_prompt.themes[:3]) + ".")
        if parsed_prompt.narrative_targets:
            intent_summary.append(
                "Narrative targets: " + ", ".join(parsed_prompt.narrative_targets[:3]) + "."
            )
        if parsed_prompt.story_outcomes:
            intent_summary.append(
                "Story outcomes: " + ", ".join(parsed_prompt.story_outcomes[:2]) + "."
            )
        if parsed_prompt.character_dynamics:
            intent_summary.append(
                "Character dynamics: " + ", ".join(parsed_prompt.character_dynamics[:2]) + "."
            )
        if parsed_prompt.year is not None:
            intent_summary.append(f"Release year: {parsed_prompt.year}.")
        if parsed_prompt.person_name:
            intent_summary.append(f"Person: {parsed_prompt.person_name}.")
        if parsed_prompt.language:
            intent_summary.append(f"Language: {parsed_prompt.language}.")
        if parsed_prompt.must_have:
            intent_summary.append("Must have: " + ", ".join(parsed_prompt.must_have[:3]) + ".")
        if parsed_prompt.avoid_genres:
            intent_summary.append("Avoid genres: " + ", ".join(parsed_prompt.avoid_genres[:3]) + ".")
        if parsed_prompt.avoid_elements:
            intent_summary.append("Avoid elements: " + ", ".join(parsed_prompt.avoid_elements[:3]) + ".")
        if intent_summary:
            parts.append(" ".join(intent_summary))
        if parsed_prompt.retrieval_summary:
            parts.append(f"Structured intent: {parsed_prompt.retrieval_summary}.")
        return " ".join(part for part in parts if part)

    def _personalize_rerank(
        self,
        movies: list[dict],
        parsed_prompt: ParsedPrompt,
        preferences: UserPreferenceResponse | None,
    ) -> list[dict]:
        if preferences is None:
            return movies

        scored_movies = [
            (
                max(len(movies) - index, 1) * 1.1
                + self._preference_score(movie, parsed_prompt, preferences),
                movie,
            )
            for index, movie in enumerate(movies)
        ]
        return [movie for _, movie in sorted(scored_movies, key=lambda item: item[0], reverse=True)]

    def _preference_score(
        self,
        movie: dict,
        parsed_prompt: ParsedPrompt,
        preferences: UserPreferenceResponse,
    ) -> float:
        genre_names = {
            self._canonical_genre_name(genre)
            for genre in self._genre_names(None, list(self._movie_genre_ids(movie)))
        }
        haystack = " ".join(
            filter(None, [movie.get("title", ""), movie.get("overview", "")])
        ).lower()
        score = 0.0

        for genre in preferences.favorite_genres:
            if self._canonical_genre_name(genre) in genre_names:
                score += 5.0
        for genre in preferences.disliked_genres:
            if self._canonical_genre_name(genre) in genre_names:
                score -= 6.0

        title = str(movie.get("title") or "").strip().lower()
        if any(title == favorite.lower() for favorite in preferences.favorite_movies):
            score += 8.0
        if any(title == disliked.lower() for disliked in preferences.disliked_movies):
            score -= 10.0

        movie_year = self._release_year(movie)
        if movie_year is not None:
            decade = f"{movie_year // 10 * 10}s"
            if decade in preferences.preferred_decades:
                score += 3.0

        vibe_preferences = {value.lower() for value in preferences.vibe_preferences}
        if "warm" in vibe_preferences and any(term in haystack for term in {"hope", "love", "connection", "family", "heart"}):
            score += 3.0
        if "emotional" in vibe_preferences and movie.get("vote_average", 0) >= 7:
            score += 2.0
        if "thoughtful" in vibe_preferences and (self._movie_genre_ids(movie) & {18, 878, 9648}):
            score += 2.5
        if "light" in vibe_preferences and self._movie_genre_ids(movie) & {35, 10749, 10751}:
            score += 2.0

        if preferences.avoid_gore:
            if self._movie_genre_ids(movie) & {27}:
                score -= 5.0
            score -= 1.5 * sum(1 for term in GORE_SIGNALS if term in haystack)

        if preferences.avoid_sad_endings:
            score -= 1.5 * sum(1 for term in SAD_ENDING_SIGNALS if term in haystack)

        complexity = (preferences.complexity_preference or "").lower()
        if complexity == "light":
            if self._movie_genre_ids(movie) & {9648}:
                score -= 2.0
            if any(term in haystack for term in {"paradox", "nonlinear", "labyrinth", "dream", "fractured"}):
                score -= 3.0
        elif complexity == "challenging":
            if self._movie_genre_ids(movie) & {9648, 878}:
                score += 2.0

        if parsed_prompt.soft_preferences and "less-confusing" in parsed_prompt.soft_preferences and complexity == "light":
            score += 1.5

        return score

    def _canonical_genre_name(self, value: str) -> str:
        normalized = value.strip().lower()
        if normalized in {"science fiction", "sci-fi", "sci fi"}:
            return "sci-fi"
        return normalized

    def _serious_similarity_prompt(self, parsed_prompt: ParsedPrompt) -> bool:
        preferences = set(parsed_prompt.soft_preferences)
        return bool(
            parsed_prompt.reference_titles
            or preferences & {"stylish", "dark", "darker", "emotional", "warmer", "less-confusing", "less-dark", "lighter", "more-hopeful", "more-emotional", "funnier", "sad", "heartbreaking", "depressing", "tragic"}
        )

    def _thoughtful_similarity_prompt(self, parsed_prompt: ParsedPrompt) -> bool:
        preferences = set(parsed_prompt.soft_preferences)
        return bool(
            parsed_prompt.reference_titles
            or preferences & {"stylish", "emotional", "warmer", "less-confusing", "less-dark", "lighter", "more-hopeful", "more-emotional", "sad", "heartbreaking", "depressing", "tragic"}
        )

    def _reference_disallows_animation(self, parsed_prompt: ParsedPrompt) -> bool:
        if self._allows_animation(parsed_prompt):
            return False
        reference_genre_ids = self._reference_genre_ids(parsed_prompt)
        return 16 not in reference_genre_ids and 10751 not in reference_genre_ids

    def _reference_is_prestige_scifi(self, parsed_prompt: ParsedPrompt) -> bool:
        reference_genre_ids = self._reference_genre_ids(parsed_prompt)
        preferences = set(parsed_prompt.soft_preferences)
        return 878 in reference_genre_ids and bool(preferences & {"stylish", "warmer", "less-confusing", "less-dark", "lighter", "more-emotional"})

    def _reference_is_blockbuster(self, parsed_prompt: ParsedPrompt) -> bool:
        reference_genre_ids = self._reference_genre_ids(parsed_prompt)
        title_blob = " ".join(parsed_prompt.reference_titles).lower()
        return 28 in reference_genre_ids or any(term in title_blob for term in {"avengers", "infinity war", "justice league", "x-men", "transformers"})

    def _prefers_sad_drama(self, parsed_prompt: ParsedPrompt) -> bool:
        preferences = set(parsed_prompt.soft_preferences)
        emotional_targets = set(parsed_prompt.emotional_targets)
        themes = set(parsed_prompt.themes)
        return bool(
            preferences & {"sad", "heartbreaking", "emotional", "depressing", "tragic", "healing", "cathartic"}
            or emotional_targets & {"sad", "heartbreaking", "emotional", "tragic", "emotional healing"}
            or themes & {"family", "family conflict", "reconciliation", "forgiveness", "recovery"}
        )

    def _healing_prompt(self, parsed_prompt: ParsedPrompt) -> bool:
        targets = (
            set(parsed_prompt.emotional_targets)
            | set(parsed_prompt.soft_preferences)
            | set(parsed_prompt.themes)
            | set(parsed_prompt.narrative_targets)
        )
        return bool(
            targets
            & {
                "healing",
                "emotional healing",
                "cathartic",
                "family-drama",
                "family drama",
                "relationship-centered",
                "relationship-centered drama",
                "warm",
                "warm but sad",
            }
            or {"family conflict", "reconciliation", "forgiveness", "recovery"} & set(parsed_prompt.themes)
        )

    def _cry_romance_prompt(self, parsed_prompt: ParsedPrompt) -> bool:
        summary = parsed_prompt.retrieval_summary.lower()
        romance_requested = bool(
            10749 in {genre["id"] for genre in parsed_prompt.hard_genres}
            or "love" in summary
            or "romantic" in summary
            or "romance" in summary
            or "heartbreaking romance" in summary
        )
        cry_requested = bool(
            {"sad", "heartbreaking", "cry-worthy", "tragic"} & set(parsed_prompt.soft_preferences)
            or {"heartbreaking", "sad", "tragic"} & set(parsed_prompt.emotional_targets)
            or "make me cry" in summary
            or "cry to" in summary
        )
        return romance_requested and cry_requested

    def _allows_animation(self, parsed_prompt: ParsedPrompt) -> bool:
        return parsed_prompt.wants_animation or parsed_prompt.wants_anime

    def _wants_family(self, parsed_prompt: ParsedPrompt) -> bool:
        return 10751 in self._required_genre_ids(parsed_prompt) or "family" == (parsed_prompt.audience or "").lower()

    def _wants_fun(self, parsed_prompt: ParsedPrompt) -> bool:
        return any(term in {"fun", "funny", "cozy", "comfort", "wholesome", "relaxing"} for term in parsed_prompt.soft_preferences)

    def _allows_documentary(self, parsed_prompt: ParsedPrompt) -> bool:
        return any("documentary" == genre["label"].lower() for genre in parsed_prompt.hard_genres)

    def _is_released_movie(self, movie: dict) -> bool:
        release_date = (movie.get("release_date") or "").replace("-", "")
        if not release_date.isdigit():
            return False
        return int(release_date) <= int(date.today().strftime("%Y%m%d"))

    def _intent_summary(self, prompt: str, parsed_prompt: ParsedPrompt) -> str:
        summary_parts = [f'Recommendations for "{prompt}".']
        if parsed_prompt.intent_family != "general":
            summary_parts.append(f"Intent family: {parsed_prompt.intent_family}.")
        if parsed_prompt.person_name:
            summary_parts.append(f"Detected a person-focused request for {parsed_prompt.person_name}.")
        elif parsed_prompt.reference_titles:
            summary_parts.append(
                f"Detected a title-similarity request based on {parsed_prompt.reference_titles[0]}."
            )
        elif parsed_prompt.year is not None:
            summary_parts.append(f"Filtered around releases from {parsed_prompt.year}.")

        if parsed_prompt.hard_genres:
            summary_parts.append(
                "Genres: " + ", ".join(genre["label"] for genre in parsed_prompt.hard_genres[:2]) + "."
            )
        if parsed_prompt.soft_preferences:
            summary_parts.append(
                "Moods: " + ", ".join(parsed_prompt.soft_preferences[:3]) + "."
            )
        if parsed_prompt.emotional_targets:
            summary_parts.append(
                "Emotional cues: " + ", ".join(parsed_prompt.emotional_targets[:3]) + "."
            )
        if parsed_prompt.narrative_targets:
            summary_parts.append(
                "Narrative targets: " + ", ".join(parsed_prompt.narrative_targets[:3]) + "."
            )
        if parsed_prompt.story_outcomes:
            summary_parts.append(
                "Narrative cues: " + ", ".join(parsed_prompt.story_outcomes[:2]) + "."
            )
        if parsed_prompt.character_dynamics:
            summary_parts.append(
                "Character dynamics: " + ", ".join(parsed_prompt.character_dynamics[:2]) + "."
            )
        if parsed_prompt.retrieval_summary:
            summary_parts.append(f"Structured interpretation: {parsed_prompt.retrieval_summary}.")
        return " ".join(summary_parts)

    def _enrich_top_movies(self, movies: list[dict]) -> None:
        for movie in movies:
            details = self._movie_details(movie["id"])
            if details.get("runtime") is not None and details["runtime"] < 40:
                continue
            movie["_details"] = details

    @classmethod
    def _cache_get(cls, key: tuple) -> dict | list[dict] | None:
        cached = cls._cache.get(key)
        if cached is None:
            return None
        expires_at, value = cached
        if expires_at < time.time():
            cls._cache.pop(key, None)
            return None
        return value

    @classmethod
    def _cache_set(cls, key: tuple, value: dict | list[dict] | None) -> None:
        cls._cache[key] = (time.time() + CACHE_TTL_SECONDS, value)

    def _image_url(self, path: str | None) -> str:
        if not path:
            return ""
        return f"{self.image_base_url}{path}"
