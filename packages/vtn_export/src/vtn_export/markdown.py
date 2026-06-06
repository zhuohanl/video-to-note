from __future__ import annotations

from decimal import Decimal
from typing import Any

from vtn_notes.assemble import assemble_markdown


def render_note_markdown(context: dict[str, Any], image_names: dict[str, str]) -> str:
    note = context["note"]
    clips = context["clips"]
    if note["include_summary"]:
        markdown = note["markdown"]
    else:
        markdown = assemble_markdown([{**clip, "summary": ""} for clip in clips])
    markdown = _rewrite_image_paths(markdown, clips, image_names)
    markdown = _apply_regen_markers(markdown, clips)
    if note["include_transcript"]:
        markdown = _append_transcripts(markdown, clips, context["transcripts"])
    return markdown.rstrip() + "\n"


def _rewrite_image_paths(
    markdown: str,
    clips: list[dict[str, Any]],
    image_names: dict[str, str],
) -> str:
    rewritten = markdown
    for clip in clips:
        old = str(clip["image_name"])
        rewritten = rewritten.replace(f"]({old})", f"]({image_names[str(clip['id'])]})")
    return rewritten


def _apply_regen_markers(markdown: str, clips: list[dict[str, Any]]) -> str:
    lines = markdown.splitlines()
    flagged = {int(clip["order_index"]) + 1 for clip in clips if clip["needs_regen"]}
    rendered: list[str] = []
    for line in lines:
        if line.startswith("## "):
            marker = _heading_number(line)
            if marker in flagged:
                rendered.append("⚠ Needs regeneration")
                rendered.append("")
        rendered.append(line)
    return "\n".join(rendered)


def _heading_number(line: str) -> int | None:
    prefix = line.removeprefix("## ").split(".", 1)[0]
    return int(prefix) if prefix.isdigit() else None


def _append_transcripts(
    markdown: str,
    clips: list[dict[str, Any]],
    transcripts: list[dict[str, Any]],
) -> str:
    rendered = markdown.rstrip()
    for clip in sorted(clips, key=lambda item: int(item["order_index"]), reverse=True):
        lines = [
            f"> {span['text']}"
            for span in transcripts
            if _overlaps(span["start_sec"], span["end_sec"], clip["start_sec"], clip["end_sec"])
        ]
        if lines:
            heading = f"## {int(clip['order_index']) + 1}. "
            start = rendered.find(heading)
            if start >= 0:
                next_start = rendered.find("\n\n## ", start + len(heading))
                insert_at = len(rendered) if next_start < 0 else next_start
                rendered = (
                    rendered[:insert_at].rstrip()
                    + "\n\n"
                    + "\n".join(lines)
                    + rendered[insert_at:]
                )
    return rendered


def _overlaps(
    span_start: Decimal,
    span_end: Decimal,
    clip_start: Decimal,
    clip_end: Decimal,
) -> bool:
    return span_start < clip_end and span_end > clip_start
