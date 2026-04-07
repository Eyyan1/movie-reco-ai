from __future__ import annotations

import hashlib
import math
import time

from openai import OpenAI

from app.core.config import settings

CACHE_TTL_SECONDS = 600


class EmbeddingService:
    _cache: dict[str, tuple[float, list[float]]] = {}

    def __init__(self) -> None:
        self.api_key = settings.openai_api_key.strip()
        self.model = settings.openai_embedding_model.strip()
        self.dimensions = max(int(settings.openai_embedding_dimensions), 1)
        self.enabled = bool(self.api_key and self.model)
        self.client = OpenAI(api_key=self.api_key) if self.enabled else None

    def get_embedding(self, text: str) -> list[float] | None:
        normalized = self._normalize_text(text)
        if not normalized or not self.enabled or self.client is None:
            return None

        cache_key = self._cache_key(normalized, self.model, self.dimensions)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=normalized,
                dimensions=self.dimensions,
            )
        except Exception:
            return None

        vector = list(response.data[0].embedding)
        self._cache_set(cache_key, vector)
        return vector

    def get_embeddings(self, texts: list[str]) -> dict[str, list[float]]:
        normalized_texts = [self._normalize_text(text) for text in texts]
        unique_texts = [text for text in dict.fromkeys(normalized_texts) if text]
        if not unique_texts or not self.enabled or self.client is None:
            return {}

        resolved: dict[str, list[float]] = {}
        missing: list[str] = []
        for text in unique_texts:
            cache_key = self._cache_key(text, self.model, self.dimensions)
            cached = self._cache_get(cache_key)
            if cached is None:
                missing.append(text)
            else:
                resolved[text] = cached

        if missing:
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=missing,
                    dimensions=self.dimensions,
                )
            except Exception:
                return resolved

            for text, item in zip(missing, response.data, strict=False):
                vector = list(item.embedding)
                cache_key = self._cache_key(text, self.model, self.dimensions)
                self._cache_set(cache_key, vector)
                resolved[text] = vector

        return resolved

    @staticmethod
    def cosine_similarity(left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        numerator = sum(a * b for a, b in zip(left, right, strict=False))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0.0 or right_norm == 0.0:
            return 0.0
        return numerator / (left_norm * right_norm)

    @staticmethod
    def _normalize_text(text: str) -> str:
        return " ".join(text.split()).strip()

    @classmethod
    def _cache_get(cls, key: str) -> list[float] | None:
        cached = cls._cache.get(key)
        if cached is None:
            return None
        expires_at, value = cached
        if expires_at < time.time():
            cls._cache.pop(key, None)
            return None
        return value

    @classmethod
    def _cache_set(cls, key: str, embedding: list[float]) -> None:
        cls._cache[key] = (time.time() + CACHE_TTL_SECONDS, embedding)

    @staticmethod
    def _cache_key(text: str, model: str, dimensions: int) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"{model}:{dimensions}:{digest}"
