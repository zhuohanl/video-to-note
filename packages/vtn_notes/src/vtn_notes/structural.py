from __future__ import annotations

from decimal import Decimal
from typing import Any


def split_clip_values(
    source: dict[str, Any],
    at_sec: Decimal,
) -> tuple[dict[str, Any], dict[str, Any]]:
    first = _base_clip(source)
    second = _base_clip(source)
    first.update(
        {
            "start_sec": source["start_sec"],
            "end_sec": at_sec,
            "title": source["title"],
            "needs_regen": True,
            "status": "ready",
        }
    )
    second.update(
        {
            "start_sec": at_sec,
            "end_sec": source["end_sec"],
            "title": f"{source['title']} (cont.)",
            "scene_at_sec": at_sec,
            "scene_blob_path": _auto_scene_blob_path(source, at_sec),
            "scene_caption": None,
            "scene_source": "auto",
            "needs_regen": True,
            "status": "ready",
        }
    )

    scene_at = source["scene_at_sec"]
    if scene_at is not None and source["start_sec"] <= scene_at < at_sec:
        first.update(_scene_fields(source))
    else:
        first.update(
            {
                "scene_at_sec": source["start_sec"],
                "scene_blob_path": _auto_scene_blob_path(source, source["start_sec"]),
                "scene_caption": None,
                "scene_source": "auto",
            }
        )
    return first, second


def merge_clip_values(clips: list[dict[str, Any]]) -> dict[str, Any]:
    first = clips[0]
    merged = _base_clip(first)
    merged.update(
        {
            "start_sec": first["start_sec"],
            "end_sec": clips[-1]["end_sec"],
            "title": first["title"],
            "summary": "\n\n".join(str(clip["summary"]) for clip in clips),
            "ai_summary": first["ai_summary"] or first["summary"],
            "needs_regen": True,
            "status": "ready",
        }
    )
    merged.update(_scene_fields(first))
    return merged


def _base_clip(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": source["summary"],
        "ai_summary": source["ai_summary"],
        "summary_seed": source["summary_seed"],
        "classification": source["classification"],
        "confidence": source["confidence"],
    }


def _scene_fields(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "scene_at_sec": source["scene_at_sec"],
        "scene_blob_path": source["scene_blob_path"],
        "scene_caption": source["scene_caption"],
        "scene_source": source["scene_source"],
    }


def _auto_scene_blob_path(source: dict[str, Any], at_sec: Decimal) -> str:
    millis = int(at_sec * 1000)
    return f"frames/auto/{source['id']}-{millis}.png"
