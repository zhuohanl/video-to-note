from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from vtn_core.models import Classification


class RefinementError(Exception):
    pass


@dataclass(frozen=True)
class CandidateClip:
    start_sec: Decimal
    end_sec: Decimal


@dataclass(frozen=True)
class RefinedClip:
    start_sec: Decimal
    end_sec: Decimal
    title: str
    summary_seed: str
    classification: Classification


class FakeRefiner:
    def __init__(self, *, invalid_json: bool = False) -> None:
        self.invalid_json = invalid_json

    def refine(self, candidates: list[CandidateClip]) -> list[RefinedClip]:
        if self.invalid_json:
            raise RefinementError("invalid refinement JSON")
        del candidates
        return [
            RefinedClip(
                Decimal("0.000"),
                Decimal("14.000"),
                "Introduction",
                "Opening architecture context",
                Classification.mixed,
            ),
            RefinedClip(
                Decimal("14.000"),
                Decimal("28.000"),
                "Progress and export",
                "Worker progress reaches reviewed export",
                Classification.visual_led,
            ),
        ]


def fallback_refine(candidates: list[CandidateClip]) -> list[RefinedClip]:
    return [
        RefinedClip(
            clip.start_sec,
            clip.end_sec,
            f"Clip {index + 1}",
            "Deterministic segment",
            Classification.mixed,
        )
        for index, clip in enumerate(candidates)
    ]
