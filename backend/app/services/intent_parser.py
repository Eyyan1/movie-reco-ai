from __future__ import annotations

import time

from openai import OpenAI

from app.core.config import settings
from app.schemas.intent import MovieIntent

CACHE_TTL_SECONDS = 600


class IntentParserService:
    _cache: dict[str, tuple[float, MovieIntent]] = {}

    def __init__(self) -> None:
        self.api_key = settings.openai_api_key.strip()
        self.model = settings.openai_model.strip()
        self.enabled = bool(self.api_key and self.model)
        self.client = OpenAI(api_key=self.api_key) if self.enabled else None

    def parse_intent(self, prompt: str) -> MovieIntent | None:
        if not self.enabled or self.client is None:
            return None

        cached = self._cache_get(prompt)
        if cached is not None:
            return cached

        instructions = (
            "Convert a movie recommendation request into structured JSON matching the schema exactly. "
            "Infer intent conservatively and decompose the request into independent signals. "
            "Allowed query_type values only: general, genre, mood, year, person, title_similarity, narrative, animation, anime, mixed_constraints. "
            "Allowed intent_family values only: romance, sad_emotional, feel_good, funny, dark_intense, reference, narrative, use_case, constraint, mixed, general. "
            "Classify prompts into human-style families. Examples: love movie -> romance, love but funny movie -> mixed, sad movie -> sad_emotional, movie to cry to -> sad_emotional, emotional family drama -> sad_emotional, healing movie with heart -> sad_emotional, movie with heart -> sad_emotional, heartfelt movie -> sad_emotional, love story that will make me cry -> mixed, feel good movie -> feel_good, comfort movie -> feel_good, cozy movie -> feel_good, wholesome movie -> feel_good, funny movie -> funny, dark thriller -> dark_intense, like Interstellar but less confusing -> reference, movie where the villain wins -> narrative, movie for date night -> use_case, not too scary horror -> constraint. "
            "Use hard constraints for explicit genre, person, year, language, animation/anime, explicit narrative ending requests, and explicit restrictions. "
            "Use soft preferences for tone, mood, themes, pacing, style, complexity, and character dynamics unless the user states them as strict requirements. "
            "Populate emotional_targets with explicit emotional aims such as sad, emotional, heartbreaking, bittersweet, warm, uplifting, tragic, healing, cathartic, cry-worthy, emotionally healing, warm but sad, cozy, comfort, wholesome, relaxing, or easy watch. "
            "Populate narrative_targets with explicit narrative aims such as villain wins, happy ending, bittersweet ending, tragic ending, revenge, sacrifice, redemption, twist ending, underdog story, or emotional healing. "
            "Populate must_have with explicit musts, nice_to_have with softer wishes, avoid_genres with explicitly rejected genres, and avoid_elements with explicit content or structural things to avoid. "
            "Support emotional intent such as sad, heartbreaking, emotional, depressing, tragic, warm, cozy, comfort, wholesome, relaxing, intense, dark, uplifting, bittersweet, romantic, healing, cathartic, cry-worthy, family drama, heartbreaking romance, relationship-centered drama, movie with heart, and heartfelt movie. "
            "Treat laugh-out-loud, witty, banter-heavy, romantic comedy, rom com, and fun entertaining movie prompts as comedy-oriented intent. "
            "Support narrative structure such as villain wins, tragic ending, happy ending, bittersweet ending, revenge, sacrifice, twist ending, underdog story, redemption arc, survival story. "
            "Support character dynamics such as ensemble cast, antihero, strong female lead, powerful villain, mentor-student, enemies to lovers, father-daughter, found family. "
            "Support formal qualities such as stylish, visually stunning, slow burn, fast paced, cerebral, less confusing, dialogue-heavy, action-heavy, easy watch. "
            "If the prompt refers to another movie, populate reference_titles and use query_type=title_similarity. "
            "For reference-title prompts, strip modifiers from the referenced title and keep modifiers such as darker, less dark, warmer, funnier, more emotional, less confusing, lighter, and more hopeful in the soft-preference fields. Resolve the referenced title conservatively and avoid polluting it with modifiers. "
            "If the prompt is mainly about a person or actor, use person and query_type=person. "
            "If animation/cartoon is explicit, set animation=true and use query_type=animation unless anime is explicit. "
            "If anime is explicit, set anime=true, animation=true, and use query_type=anime. "
            "Return valid schema-shaped JSON only."
        )

        for _ in range(2):
            try:
                response = self.client.responses.parse(
                    model=self.model,
                    input=[
                        {"role": "developer", "content": instructions},
                        {"role": "user", "content": prompt},
                    ],
                    text_format=MovieIntent,
                )
                parsed = response.output_parsed
                if parsed is not None:
                    normalized = MovieIntent.model_validate(parsed.model_dump())
                    self._cache_set(prompt, normalized)
                    return normalized
            except Exception:
                continue
        return None

    def build_retrieval_summary(self, intent: MovieIntent) -> str:
        parts: list[str] = []
        if intent.intent_family and intent.intent_family != "general":
            parts.append(f"intent family: {intent.intent_family}")
        if intent.reference_titles:
            parts.append(f"similar to {intent.reference_titles[0]}")
        if intent.person:
            parts.append(f"starring {intent.person}")
        if intent.genres:
            parts.append(", ".join(intent.genres[:3]))
        if intent.subgenres:
            parts.append(", ".join(intent.subgenres[:2]))
        if intent.tone:
            parts.append(f"tone: {', '.join(intent.tone[:3])}")
        if intent.moods:
            parts.append(f"mood: {', '.join(intent.moods[:3])}")
        if intent.emotional_targets:
            parts.append(f"emotional targets: {', '.join(intent.emotional_targets[:4])}")
        if intent.themes:
            parts.append(f"themes: {', '.join(intent.themes[:3])}")
        if intent.narrative_targets:
            parts.append(f"narrative targets: {', '.join(intent.narrative_targets[:4])}")
        if intent.story_outcomes:
            parts.append(f"story outcomes: {', '.join(intent.story_outcomes[:2])}")
        if intent.ending_type:
            parts.append(f"ending: {intent.ending_type}")
        if intent.character_dynamics:
            parts.append(f"character dynamics: {', '.join(intent.character_dynamics[:2])}")
        if intent.setting:
            parts.append(f"setting: {', '.join(intent.setting[:2])}")
        if intent.scale:
            parts.append(f"scale: {intent.scale}")
        if intent.pacing:
            parts.append(f"pacing: {intent.pacing}")
        if intent.complexity:
            parts.append(f"complexity: {intent.complexity}")
        if intent.violence_level:
            parts.append(f"violence: {intent.violence_level}")
        if intent.audience:
            parts.append(f"audience: {intent.audience}")
        if intent.year is not None:
            parts.append(f"year: {intent.year}")
        if intent.release_preference:
            parts.append(f"release preference: {intent.release_preference}")
        if intent.language:
            parts.append(f"language: {intent.language}")
        if intent.must_have:
            parts.append(f"must have: {', '.join(intent.must_have[:4])}")
        if intent.nice_to_have:
            parts.append(f"nice to have: {', '.join(intent.nice_to_have[:4])}")
        if intent.avoid_genres:
            parts.append(f"avoid genres: {', '.join(intent.avoid_genres[:3])}")
        if intent.avoid_elements:
            parts.append(f"avoid elements: {', '.join(intent.avoid_elements[:4])}")
        if intent.exclude_terms:
            parts.append(f"exclude: {', '.join(intent.exclude_terms[:4])}")
        if not parts:
            return "general movie recommendation"
        return "; ".join(parts)

    @classmethod
    def _cache_get(cls, prompt: str) -> MovieIntent | None:
        cached = cls._cache.get(prompt)
        if cached is None:
            return None
        expires_at, value = cached
        if expires_at < time.time():
            cls._cache.pop(prompt, None)
            return None
        return value

    @classmethod
    def _cache_set(cls, prompt: str, intent: MovieIntent) -> None:
        cls._cache[prompt] = (time.time() + CACHE_TTL_SECONDS, intent)
