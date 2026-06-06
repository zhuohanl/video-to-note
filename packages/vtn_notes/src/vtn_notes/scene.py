from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SceneCandidate:
    at_sec: Decimal
    event_type: str
    confidence: float
    phash: str | None
    frame_blob_path: str


def _hamming(left: str, right: str) -> int:
    return int(left, 16).__xor__(int(right, 16)).bit_count()


def _score(candidate: SceneCandidate) -> float:
    weights = {"slide": 1.0, "title": 1.1, "demo": 1.2, "code": 1.0, "speaker": 0.4}
    return weights.get(candidate.event_type, 0.5) * candidate.confidence


def choose_scene(candidates: list[SceneCandidate], *, phash_threshold: int = 1) -> SceneCandidate:
    if not candidates:
        raise ValueError("at least one scene candidate is required")

    deduped: list[SceneCandidate] = []
    for candidate in sorted(candidates, key=_score, reverse=True):
        if candidate.phash and any(
            existing.phash and _hamming(candidate.phash, existing.phash) <= phash_threshold
            for existing in deduped
        ):
            continue
        deduped.append(candidate)
    return max(deduped, key=_score)
