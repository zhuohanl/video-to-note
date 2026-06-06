from __future__ import annotations

from dataclasses import dataclass
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
