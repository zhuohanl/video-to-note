from __future__ import annotations

from dataclasses import dataclass

from vtn_core.settings import SegmentationSettings

from vtn_segment.detectors import BoundaryCandidate


@dataclass(frozen=True)
class FusedBoundary:
    at_sec: float
    score: float
    signal_types: set[str]


def _nearest(value: float, candidates: list[float]) -> float:
    if not candidates:
        return value
    return min(candidates, key=lambda candidate: abs(candidate - value))


def _snap(
    value: float,
    transcript_starts: list[float],
    slide_times: list[float],
    window: float,
) -> float:
    snapped = _nearest(value, transcript_starts)
    slide = _nearest(snapped, slide_times)
    if abs(slide - snapped) <= window:
        return slide
    return snapped


def fuse_boundaries(
    candidates: list[BoundaryCandidate],
    *,
    transcript_starts: list[float],
    slide_times: list[float],
    settings: SegmentationSettings,
) -> list[FusedBoundary]:
    clusters: list[list[BoundaryCandidate]] = []
    for candidate in sorted(candidates, key=lambda item: item.at_sec):
        if clusters and candidate.at_sec - clusters[-1][-1].at_sec <= settings.merge_window_sec:
            clusters[-1].append(candidate)
        else:
            clusters.append([candidate])

    fused: list[FusedBoundary] = []
    for cluster in clusters:
        score = sum(settings.weights.get(item.signal_type, 0.0) * item.strength for item in cluster)
        if score < settings.min_score:
            continue
        strength_sum = sum(item.strength for item in cluster) or 1.0
        mean = sum(item.at_sec * item.strength for item in cluster) / strength_sum
        fused.append(
            FusedBoundary(
                at_sec=_snap(mean, transcript_starts, slide_times, settings.merge_window_sec),
                score=score,
                signal_types={item.signal_type for item in cluster},
            )
        )
    return fused
