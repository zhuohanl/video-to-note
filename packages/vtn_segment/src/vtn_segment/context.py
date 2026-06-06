from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TimelineContext:
    transcript_spans: list[dict[str, object]]
    visual_events: list[dict[str, object]]
