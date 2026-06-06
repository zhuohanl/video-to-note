from __future__ import annotations

from pydantic import BaseModel, Field


class ArtifactSettings(BaseModel):
    stale_timeout_sec: float = 900.0
    wait_timeout_sec: float = 30.0
    poll_interval_sec: float = 0.1


class SegmentationSettings(BaseModel):
    merge_window_sec: float = 4.0
    min_score: float = 0.5
    weights: dict[str, float] = Field(
        default_factory=lambda: {
            "semantic_shift": 0.6,
            "speaker_change": 0.4,
            "time_gap": 0.3,
            "slide_change": 0.7,
            "title_change": 0.7,
            "demo_change": 0.5,
        }
    )
