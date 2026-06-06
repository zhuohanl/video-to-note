from __future__ import annotations

import re
from decimal import Decimal
from typing import Any


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "clip"


def _time_range(start_sec: Decimal, end_sec: Decimal) -> str:
    return f"{start_sec:.3f}s-{end_sec:.3f}s"


def image_name(order_index: int, title: str) -> str:
    return f"images/{order_index + 1:04d}-{_slug(title)}.png"


def assemble_markdown(clips: list[dict[str, Any]]) -> str:
    sections: list[str] = []
    for clip in clips:
        order = int(clip["order_index"]) + 1
        title = str(clip["title"])
        image_path = image_name(int(clip["order_index"]), title)
        caption = clip.get("scene_caption") or ""
        sections.append(
            "\n".join(
                [
                    f"## {order}. {title}",
                    "",
                    f"Time: {_time_range(clip['start_sec'], clip['end_sec'])}",
                    "",
                    f"![{title}]({image_path})",
                    "",
                    str(caption),
                    "",
                    str(clip["summary"]),
                ]
            ).strip()
        )
    return "\n\n".join(sections) + "\n"
