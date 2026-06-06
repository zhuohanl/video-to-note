from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class VisualEventData:
    at_sec: Decimal
    event_type: str
    confidence: float
    ocr_text: str | None
    phash: str | None
    frame_blob_path: str | None


class FakeFrameSampler:
    def sample(self, video_id: UUID) -> list[VisualEventData]:
        return [
            VisualEventData(
                Decimal("1.000"),
                "slide",
                0.95,
                "Architecture overview",
                "8f1c2a3b4d5e6071",
                f"frames/{video_id}/0001.png",
            ),
            VisualEventData(
                Decimal("5.000"),
                "slide",
                0.94,
                "Browser never calls worker",
                "8f1c2a3b4d5e6070",
                f"frames/{video_id}/0002.png",
            ),
            VisualEventData(
                Decimal("9.000"),
                "demo",
                0.89,
                "Submit job",
                "1a2b3c4d5e6f7081",
                f"frames/{video_id}/0003.png",
            ),
            VisualEventData(
                Decimal("14.000"),
                "code",
                0.9,
                "QueueProvider",
                "2b3c4d5e6f708192",
                f"frames/{video_id}/0004.png",
            ),
            VisualEventData(
                Decimal("19.000"),
                "speaker",
                0.8,
                None,
                "3c4d5e6f708192a3",
                f"frames/{video_id}/0005.png",
            ),
            VisualEventData(
                Decimal("25.000"),
                "slide",
                0.93,
                "Export ZIP",
                "4d5e6f708192a3b4",
                f"frames/{video_id}/0006.png",
            ),
        ]


class FakeOcr:
    def extract_text(self, frame_blob_path: str) -> str:
        del frame_blob_path
        return ""
