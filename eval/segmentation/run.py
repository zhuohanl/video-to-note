from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vtn_core.settings import SegmentationSettings
from vtn_segment.detectors import BoundaryCandidate
from vtn_segment.fusion import FusedBoundary, fuse_boundaries

LABEL_DIR = Path(__file__).parent / "labels"


@dataclass(frozen=True)
class MetricResult:
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float


def score_boundaries(
    predicted: list[float],
    expected: list[float],
    *,
    tolerance_sec: float,
) -> MetricResult:
    unmatched_expected = set(range(len(expected)))
    true_positives = 0
    false_positives = 0

    for boundary in predicted:
        match = _nearest_match(boundary, expected, unmatched_expected, tolerance_sec)
        if match is None:
            false_positives += 1
            continue
        unmatched_expected.remove(match)
        true_positives += 1

    false_negatives = len(unmatched_expected)
    precision = true_positives / (true_positives + false_positives or 1)
    recall = true_positives / (true_positives + false_negatives or 1)
    return MetricResult(
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
    )


def evaluate_label(
    path: Path,
    settings: SegmentationSettings,
) -> tuple[str, list[FusedBoundary], MetricResult]:
    payload = json.loads(path.read_text())
    candidates = [
        BoundaryCandidate(
            at_sec=float(item["at_sec"]),
            signal_type=str(item["signal_type"]),
            strength=float(item["strength"]),
            evidence=dict(item.get("evidence", {})),
        )
        for item in payload["candidates"]
    ]
    fused = fuse_boundaries(
        candidates,
        transcript_starts=[float(item) for item in payload["transcript_starts"]],
        slide_times=[float(item) for item in payload["slide_times"]],
        settings=settings,
    )
    result = score_boundaries(
        [boundary.at_sec for boundary in fused],
        [float(item) for item in payload["labeled_boundaries"]],
        tolerance_sec=float(payload.get("tolerance_sec", 3.0)),
    )
    return str(payload["id"]), fused, result


def run(
    label_dir: Path = LABEL_DIR,
    settings: SegmentationSettings | None = None,
) -> dict[str, Any]:
    active_settings = settings or SegmentationSettings()
    reports = []
    totals = MetricResult(0, 0, 0, 0.0, 0.0)
    for path in sorted(label_dir.glob("*.json")):
        label_id, fused, result = evaluate_label(path, active_settings)
        reports.append(
            {
                "id": label_id,
                "predicted": [round(boundary.at_sec, 3) for boundary in fused],
                "precision": round(result.precision, 3),
                "recall": round(result.recall, 3),
                "true_positives": result.true_positives,
                "false_positives": result.false_positives,
                "false_negatives": result.false_negatives,
            }
        )
        totals = MetricResult(
            true_positives=totals.true_positives + result.true_positives,
            false_positives=totals.false_positives + result.false_positives,
            false_negatives=totals.false_negatives + result.false_negatives,
            precision=0.0,
            recall=0.0,
        )

    summary = score_from_counts(
        totals.true_positives,
        totals.false_positives,
        totals.false_negatives,
    )
    return {
        "labels": reports,
        "summary": {
            "precision": round(summary.precision, 3),
            "recall": round(summary.recall, 3),
            "true_positives": summary.true_positives,
            "false_positives": summary.false_positives,
            "false_negatives": summary.false_negatives,
        },
        "settings": active_settings.model_dump(),
    }


def score_from_counts(
    true_positives: int,
    false_positives: int,
    false_negatives: int,
) -> MetricResult:
    precision = true_positives / (true_positives + false_positives or 1)
    recall = true_positives / (true_positives + false_negatives or 1)
    return MetricResult(true_positives, false_positives, false_negatives, precision, recall)


def _nearest_match(
    boundary: float,
    expected: list[float],
    unmatched_expected: set[int],
    tolerance_sec: float,
) -> int | None:
    candidates = [
        (index, abs(boundary - expected[index]))
        for index in unmatched_expected
        if abs(boundary - expected[index]) <= tolerance_sec
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda item: item[1])[0]


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
