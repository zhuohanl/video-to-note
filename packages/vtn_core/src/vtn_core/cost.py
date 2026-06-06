from __future__ import annotations

from decimal import Decimal
from math import ceil

from vtn_core.models import PromptDepth


def estimate(duration_sec: Decimal | None, depth: PromptDepth) -> dict[str, object]:
    duration = duration_sec or Decimal("300.000")
    expected_clips = max(1, ceil(float(duration) / 300.0))
    depth_multiplier = {
        PromptDepth.brief: Decimal("0.75"),
        PromptDepth.balanced: Decimal("1.00"),
        PromptDepth.thorough: Decimal("1.50"),
        PromptDepth.custom: Decimal("1.10"),
    }[depth]
    llm_calls = expected_clips + 2
    audio_min = duration / Decimal("60")
    ocr_frames = max(1, ceil(float(duration) / 30.0))
    usd = (
        Decimal(llm_calls) * Decimal("0.010")
        + audio_min * Decimal("0.002")
        + Decimal(ocr_frames) * Decimal("0.001")
    ) * depth_multiplier
    return {
        "usd": f"{usd.quantize(Decimal('0.0001'))}",
        "breakdown": {
            "profile": "submit_default" if duration_sec is None else "resolved",
            "duration_sec": f"{duration.quantize(Decimal('0.001'))}",
            "expected_clips": expected_clips,
            "llm_calls": llm_calls,
            "transcript_provider": "auto",
            "ocr_frames": ocr_frames,
            "depth": depth.value,
        },
    }


def actual_from_usage(
    *,
    transcript_end_sec: Decimal,
    ocr_frames: int,
    clip_count: int,
    tokens: int = 0,
) -> dict[str, object]:
    audio_min = transcript_end_sec / Decimal("60")
    llm_calls = clip_count + 2
    usd = (
        Decimal(llm_calls) * Decimal("0.010")
        + audio_min * Decimal("0.002")
        + Decimal(ocr_frames) * Decimal("0.001")
    )
    return {
        "usd": f"{usd.quantize(Decimal('0.0001'))}",
        "tokens": tokens,
        "audio_min": float(audio_min.quantize(Decimal("0.001"))),
        "ocr_frames": ocr_frames,
        "llm_calls": llm_calls,
    }
