from __future__ import annotations

from pydantic import BaseModel, Field


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
