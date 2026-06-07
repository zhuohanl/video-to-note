from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from vtn_core.models import TranscriptSource


@dataclass(frozen=True)
class TranscriptSpanData:
    start_sec: Decimal
    end_sec: Decimal
    text: str
    speaker: str | None


@dataclass(frozen=True)
class TranscriptResult:
    source: TranscriptSource
    spans: list[TranscriptSpanData]
    warning: tuple[str, str] | None = None


class FakeTranscriptProvider:
    def __init__(self, *, force_asr_fallback: bool = False) -> None:
        self.force_asr_fallback = force_asr_fallback

    def fetch(self, video_id: UUID) -> TranscriptResult:
        del video_id
        source = (
            TranscriptSource.azure_speech
            if self.force_asr_fallback
            else TranscriptSource.youtube_captions
        )
        warning = (
            ("asr_fallback", "Using Azure Speech fallback") if self.force_asr_fallback else None
        )
        return TranscriptResult(
            source=source,
            warning=warning,
            spans=[
                TranscriptSpanData(Decimal("0.000"), Decimal("4.200"), "Welcome.", "Speaker 1"),
                TranscriptSpanData(
                    Decimal("4.200"),
                    Decimal("10.000"),
                    "Architecture.",
                    "Speaker 1",
                ),
                TranscriptSpanData(
                    Decimal("10.000"),
                    Decimal("16.000"),
                    "Worker events.",
                    "Speaker 1",
                ),
                TranscriptSpanData(
                    Decimal("16.000"),
                    Decimal("22.000"),
                    "API streams.",
                    "Speaker 1",
                ),
                TranscriptSpanData(
                    Decimal("22.000"),
                    Decimal("28.000"),
                    "Review export.",
                    "Speaker 1",
                ),
            ],
        )
