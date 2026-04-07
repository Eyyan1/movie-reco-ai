from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean

from fastapi import HTTPException

from app.schemas.recommendation import RecommendationGroup, RecommendationResponse
from app.services.tmdb_service import TMDBService


DEFAULT_BENCHMARK_PATH = Path(__file__).with_name("benchmark_prompts.json")

FAMILY_PRIMARY_GENRES = {
    "romance": {"romance", "drama", "comedy"},
    "sad_emotional": {"drama", "romance", "family"},
    "feel_good": {"comedy", "family", "romance", "adventure"},
    "funny": {"comedy", "romance"},
    "dark_intense": {"thriller", "mystery", "drama", "horror"},
    "reference": {"science fiction", "drama", "thriller", "mystery", "action"},
    "narrative": {"drama", "thriller", "mystery", "romance"},
    "use_case": {"romance", "comedy", "family", "drama"},
    "mixed": {"romance", "comedy", "drama", "science fiction", "thriller", "animation"},
    "constraint": {"horror", "thriller", "drama"},
    "general": set(),
}

FAMILY_DISCOURAGED_GENRES = {
    "romance": {"horror", "crime", "war", "action"},
    "sad_emotional": {"action", "comedy", "horror", "science fiction"},
    "feel_good": {"horror", "thriller", "crime"},
    "funny": {"horror", "thriller", "war", "crime"},
    "dark_intense": {"family", "comedy"},
    "reference": {"family", "animation"},
    "narrative": {"family", "comedy"},
    "use_case": {"horror", "crime"},
    "mixed": {"horror", "crime"},
    "constraint": {"gore", "slasher", "extreme horror"},
    "general": set(),
}

TEXT_SIGNAL_MAP = {
    "sad": {"grief", "loss", "heartbreak", "mourning", "loneliness", "tragedy", "terminal"},
    "emotional": {"family", "memory", "love", "connection", "healing", "humanity"},
    "heartbreaking": {"heartbreak", "tragic", "goodbye", "loss", "separation"},
    "bittersweet": {"bittersweet", "memory", "parting", "reunion", "longing"},
    "warm": {"hope", "healing", "friendship", "kindness", "support", "reunion", "joy"},
    "uplifting": {"hope", "inspiring", "joy", "second chance", "support", "healing"},
    "funny": {"funny", "laugh", "banter", "chaos", "hilarious"},
    "romantic": {"love", "relationship", "romance", "couple", "marriage", "reunion"},
    "dark": {"dark", "obsession", "danger", "mystery", "doom", "despair"},
    "thoughtful": {"humanity", "identity", "future", "memory", "space", "consciousness"},
    "cozy": {"warm", "comfort", "home", "friendship", "family"},
    "villain wins": {"defeat", "doomed", "collapse", "corruption", "darkness", "final loss"},
    "tragic ending": {"tragic", "death", "mourning", "loss", "sacrifice"},
    "bittersweet ending": {"bittersweet", "parting", "reunion", "memory", "hope"},
    "happy ending": {"happy ending", "joy", "reunion", "hope", "healing"},
    "revenge": {"revenge", "vengeance", "retaliation", "payback"},
    "sacrifice": {"sacrifice", "selfless", "save others"},
    "redemption": {"redemption", "forgiveness", "atonement", "second chance"},
    "twist ending": {"twist", "reveal", "secret", "unexpected"},
    "underdog story": {"underdog", "against all odds", "unlikely", "comeback"},
    "emotional healing": {"healing", "recovery", "acceptance", "support", "reunion"}
}

NEGATIVE_TEXT_SIGNALS = {
    "sad_emotional": {"superhero", "franchise", "explosive", "mission", "blockbuster"},
    "romance": {"serial killer", "drug cartel", "battlefield", "war zone"},
    "funny": {"bleak", "terminal", "mourning"},
    "feel_good": {"grim", "tragic", "doom", "murder"},
    "reference": {"family fun", "playful animation"},
    "narrative": {"family fun", "cheerful", "lighthearted"},
}


@dataclass(frozen=True)
class BenchmarkPrompt:
    prompt: str
    intent_family: str
    expected_genres: list[str]
    discouraged_genres: list[str]
    expected_moods: list[str]
    expected_story_outcomes: list[str]
    notes: str


@dataclass(frozen=True)
class BenchmarkMetrics:
    family_match_score: float
    genre_alignment_score: float
    mood_alignment_score: float
    narrative_alignment_score: float
    mismatch_penalty_score: float
    overall_score: float


@dataclass(frozen=True)
class BenchmarkRunResult:
    prompt: str
    family: str
    metrics: BenchmarkMetrics
    failure_reasons: list[str]
    best_group_title: str
    top_titles: list[str]
    failed: bool
    failure_reason: str | None


def load_benchmark_prompts(path: Path | None = None) -> list[BenchmarkPrompt]:
    benchmark_path = path or DEFAULT_BENCHMARK_PATH
    payload = json.loads(benchmark_path.read_text(encoding="utf-8"))
    prompts = payload["prompts"]
    return [
        BenchmarkPrompt(
            prompt=item["prompt"],
            intent_family=item.get("intent_family", "general"),
            expected_genres=item.get("expected_genres", []),
            discouraged_genres=item.get("discouraged_genres", []),
            expected_moods=item.get("expected_moods", []),
            expected_story_outcomes=item.get("expected_story_outcomes", []),
            notes=item.get("notes", ""),
        )
        for item in prompts
    ]


def evaluate_prompt(service: TMDBService, benchmark: BenchmarkPrompt) -> BenchmarkRunResult:
    try:
        response = service.get_recommendations(benchmark.prompt)
    except HTTPException as exc:
        return _failed_result(benchmark, exc.detail if exc.detail else str(exc))
    except Exception as exc:
        return _failed_result(benchmark, str(exc))

    parsed_prompt = service._parse_prompt(benchmark.prompt)
    best_group = _best_match_group(response)
    genres_per_movie = [_split_genres(movie.genre) for movie in best_group.movies]
    texts = [_movie_text(movie) for movie in best_group.movies]

    family_match = _family_match_score(benchmark, genres_per_movie)
    genre_alignment = _genre_alignment_score(benchmark, genres_per_movie)
    mood_alignment = _text_alignment_score(benchmark.expected_moods or parsed_prompt.emotional_targets or parsed_prompt.soft_preferences, texts)
    narrative_alignment = _text_alignment_score(
        benchmark.expected_story_outcomes or parsed_prompt.narrative_targets or parsed_prompt.story_outcomes,
        texts,
    )
    mismatch_penalty = _mismatch_penalty_score(benchmark, genres_per_movie, texts)
    overall = _clamp01(
        0.25 * family_match
        + 0.25 * genre_alignment
        + 0.2 * mood_alignment
        + 0.15 * narrative_alignment
        + 0.15 * mismatch_penalty
    )

    failure_reasons = _failure_reasons(
        benchmark=benchmark,
        family_match_score=family_match,
        genre_alignment_score=genre_alignment,
        mood_alignment_score=mood_alignment,
        narrative_alignment_score=narrative_alignment,
        mismatch_penalty_score=mismatch_penalty,
        genres_per_movie=genres_per_movie,
        texts=texts,
    )

    return BenchmarkRunResult(
        prompt=benchmark.prompt,
        family=benchmark.intent_family,
        metrics=BenchmarkMetrics(
            family_match_score=family_match,
            genre_alignment_score=genre_alignment,
            mood_alignment_score=mood_alignment,
            narrative_alignment_score=narrative_alignment,
            mismatch_penalty_score=mismatch_penalty,
            overall_score=overall,
        ),
        failure_reasons=failure_reasons,
        best_group_title=best_group.group_title,
        top_titles=[movie.title for movie in best_group.movies[:6]],
        failed=False,
        failure_reason=None,
    )


def summarize_results(results: list[BenchmarkRunResult]) -> dict[str, object]:
    family_scores: dict[str, list[float]] = {}
    failure_counts: dict[str, int] = {}
    failed_count = 0
    for result in results:
        family_scores.setdefault(result.family, []).append(result.metrics.overall_score)
        if result.failed:
            failed_count += 1
            if result.failure_reason:
                failure_counts[result.failure_reason] = failure_counts.get(result.failure_reason, 0) + 1
        for reason in result.failure_reasons:
            failure_counts[reason] = failure_counts.get(reason, 0) + 1

    overall_average = mean(result.metrics.overall_score for result in results) if results else 0.0
    averages_by_family = {
        family: mean(scores)
        for family, scores in sorted(family_scores.items())
    }
    worst_prompts = sorted(results, key=lambda item: item.metrics.overall_score)[:5]
    best_prompts = sorted(results, key=lambda item: item.metrics.overall_score, reverse=True)[:5]
    top_failure_reasons = sorted(failure_counts.items(), key=lambda item: item[1], reverse=True)[:8]

    return {
        "total_prompts": len(results),
        "succeeded": len(results) - failed_count,
        "failed": failed_count,
        "overall_average": overall_average,
        "averages_by_family": averages_by_family,
        "worst_prompts": [asdict(result) for result in worst_prompts],
        "best_prompts": [asdict(result) for result in best_prompts],
        "top_failure_reasons": top_failure_reasons,
        "results": [asdict(result) for result in results],
    }


def _failed_result(benchmark: BenchmarkPrompt, failure_reason: str) -> BenchmarkRunResult:
    reason = failure_reason.strip() or "Unknown benchmark failure."
    return BenchmarkRunResult(
        prompt=benchmark.prompt,
        family=benchmark.intent_family,
        metrics=BenchmarkMetrics(
            family_match_score=0.0,
            genre_alignment_score=0.0,
            mood_alignment_score=0.0,
            narrative_alignment_score=0.0,
            mismatch_penalty_score=0.0,
            overall_score=0.0,
        ),
        failure_reasons=["recommendation failure"],
        best_group_title="FAILED",
        top_titles=[],
        failed=True,
        failure_reason=reason,
    )


def _best_match_group(response: RecommendationResponse) -> RecommendationGroup:
    for group in response.groups:
        if group.group_title.lower() == "best match":
            return group
    return response.groups[0]


def _movie_text(movie: object) -> str:
    return " ".join(
        part
        for part in [
            getattr(movie, "title", ""),
            getattr(movie, "genre", ""),
            getattr(movie, "tagline", ""),
            getattr(movie, "reason", ""),
        ]
        if part
    ).lower()


def _split_genres(value: str) -> set[str]:
    return {item.strip().lower() for item in value.split(",") if item.strip()}


def _family_match_score(benchmark: BenchmarkPrompt, genres_per_movie: list[set[str]]) -> float:
    primary = FAMILY_PRIMARY_GENRES.get(benchmark.intent_family, set()) | {
        genre.strip().lower() for genre in benchmark.expected_genres
    }
    if not primary:
        return 1.0
    hits = sum(1 for genres in genres_per_movie if genres & primary)
    ratio = hits / max(len(genres_per_movie), 1)
    return _clamp01(ratio / 0.67)


def _genre_alignment_score(benchmark: BenchmarkPrompt, genres_per_movie: list[set[str]]) -> float:
    expected = {genre.strip().lower() for genre in benchmark.expected_genres}
    discouraged = {
        genre.strip().lower() for genre in benchmark.discouraged_genres
    } | FAMILY_DISCOURAGED_GENRES.get(benchmark.intent_family, set())
    if not genres_per_movie:
        return 0.0

    expected_hits = sum(1 for genres in genres_per_movie if not expected or genres & expected)
    discouraged_hits = sum(1 for genres in genres_per_movie if genres & discouraged)
    positive = expected_hits / len(genres_per_movie)
    negative = discouraged_hits / len(genres_per_movie)
    return _clamp01(positive - 0.6 * negative)


def _text_alignment_score(targets: list[str], texts: list[str]) -> float:
    normalized_targets = [target.strip().lower() for target in targets if target.strip()]
    if not normalized_targets:
        return 1.0
    hits = 0.0
    for target in normalized_targets:
        keywords = TEXT_SIGNAL_MAP.get(target, {target})
        if any(any(keyword in text for keyword in keywords) for text in texts):
            hits += 1.0
    return _clamp01(hits / len(normalized_targets))


def _mismatch_penalty_score(
    benchmark: BenchmarkPrompt,
    genres_per_movie: list[set[str]],
    texts: list[str],
) -> float:
    discouraged = {
        genre.strip().lower() for genre in benchmark.discouraged_genres
    } | FAMILY_DISCOURAGED_GENRES.get(benchmark.intent_family, set())
    genre_mismatches = sum(1 for genres in genres_per_movie if genres & discouraged)
    text_penalties = NEGATIVE_TEXT_SIGNALS.get(benchmark.intent_family, set())
    text_mismatches = sum(1 for text in texts if any(signal in text for signal in text_penalties))
    total = len(genres_per_movie) + len(texts)
    if total == 0:
        return 0.0
    mismatch_ratio = (genre_mismatches + text_mismatches) / total
    return _clamp01(1.0 - mismatch_ratio)


def _failure_reasons(
    *,
    benchmark: BenchmarkPrompt,
    family_match_score: float,
    genre_alignment_score: float,
    mood_alignment_score: float,
    narrative_alignment_score: float,
    mismatch_penalty_score: float,
    genres_per_movie: list[set[str]],
    texts: list[str],
) -> list[str]:
    reasons: list[str] = []
    if family_match_score < 0.6:
        reasons.append("weak family coherence")
    if genre_alignment_score < 0.55:
        reasons.append("genre drift")
    if mood_alignment_score < 0.45 and benchmark.expected_moods:
        reasons.append("weak mood alignment")
    if narrative_alignment_score < 0.45 and benchmark.expected_story_outcomes:
        reasons.append("weak narrative alignment")
    if mismatch_penalty_score < 0.55:
        reasons.append("discouraged leakage")

    discouraged = {
        genre.strip().lower() for genre in benchmark.discouraged_genres
    } | FAMILY_DISCOURAGED_GENRES.get(benchmark.intent_family, set())
    if any(genres & discouraged for genres in genres_per_movie):
        reasons.append("discouraged genres in best match")
    if benchmark.intent_family == "reference" and any("animation" in genres for genres in genres_per_movie):
        reasons.append("reference drift into animation")
    if benchmark.intent_family == "sad_emotional" and any(
        any(signal in text for signal in {"superhero", "franchise", "explosive"}) for text in texts
    ):
        reasons.append("spectacle-heavy emotional mismatch")
    return reasons[:5]


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))
