from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import sqrt
from typing import Protocol


@dataclass(frozen=True)
class BoundaryCandidate:
    at_sec: float
    signal_type: str
    strength: float
    evidence: dict[str, object]


class BoundaryDetector(Protocol):
    name: str

    def detect(self, ctx: object) -> list[BoundaryCandidate]: ...


class EmbeddingModel(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SemanticShiftDetector:
    name = "semantic_shift"

    def __init__(self, *, embedding_model: EmbeddingModel, threshold: float) -> None:
        self.embedding_model = embedding_model
        self.threshold = threshold

    def detect(self, ctx: object) -> list[BoundaryCandidate]:
        texts = list(ctx) if isinstance(ctx, Iterable) and not isinstance(ctx, str) else [ctx]
        if len(texts) < 2:
            return []
        vectors = self.embedding_model.embed([str(text) for text in texts])
        candidates: list[BoundaryCandidate] = []
        for index in range(1, len(vectors)):
            distance = 1.0 - _cosine(vectors[index - 1], vectors[index])
            if distance >= self.threshold:
                candidates.append(
                    BoundaryCandidate(
                        at_sec=float(index),
                        signal_type=self.name,
                        strength=min(1.0, distance),
                        evidence={"left_index": index - 1, "right_index": index},
                    )
                )
        return candidates


def _cosine(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
