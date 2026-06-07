from __future__ import annotations

from typing import Any


def build_metadata(context: dict[str, Any], image_names: dict[str, str]) -> dict[str, Any]:
    return {
        "source_url": context["source_url"],
        "depth": context["prompt"]["depth"],
        "style_profile": context["prompt"].get("style_profile") or {},
        "transcript_source": _transcript_source(context["transcripts"]),
        "clips": [
            {
                "id": str(clip["id"]),
                "order_index": clip["order_index"],
                "start_sec": str(clip["start_sec"]),
                "end_sec": str(clip["end_sec"]),
                "title": clip["title"],
                "scene_at_sec": (
                    str(clip["scene_at_sec"]) if clip["scene_at_sec"] is not None else None
                ),
                "scene_path": image_names[str(clip["id"])],
            }
            for clip in context["clips"]
        ],
    }


def _transcript_source(transcripts: list[dict[str, Any]]) -> str | None:
    if not transcripts:
        return None
    return str(transcripts[0]["source"])
