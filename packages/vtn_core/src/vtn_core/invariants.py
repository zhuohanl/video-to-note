from __future__ import annotations

import io
import json
import re
import zipfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any


class InvariantError(AssertionError):
    """Raised when persisted or exported state violates a hard product invariant."""


def _get(item: object, name: str) -> Any:
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name)


def assert_note_no_transcript(markdown: str) -> None:
    if re.search(r"(?m)^\s*>", markdown):
        raise InvariantError("note markdown must not persist transcript blockquotes")


def assert_note_no_regen_marker(markdown: str) -> None:
    if "Needs regeneration" in markdown:
        raise InvariantError("note markdown must not persist regeneration markers")


def assert_clips_contiguous_ordered(clips: Iterable[object]) -> None:
    ordered = sorted(clips, key=lambda clip: int(_get(clip, "order_index")))
    expected = list(range(len(ordered)))
    actual = [int(_get(clip, "order_index")) for clip in ordered]
    if actual != expected:
        raise InvariantError(f"clip order_index values must be contiguous: {actual}")

    previous_end: float | None = None
    for clip in ordered:
        start = float(_get(clip, "start_sec"))
        end = float(_get(clip, "end_sec"))
        if end < start:
            raise InvariantError("clip time range is invalid")
        if previous_end is not None and start < previous_end:
            raise InvariantError("clip time ranges overlap")
        previous_end = end


def assert_unique_order_index(clips: Iterable[object]) -> None:
    indexes = [int(_get(clip, "order_index")) for clip in clips]
    if len(indexes) != len(set(indexes)):
        raise InvariantError("Duplicate clip order_index values are not allowed")


def assert_baseline_immutable(versions: Iterable[object]) -> None:
    baselines = [
        version
        for version in versions
        if int(_get(version, "seq")) == 1
        and bool(_get(version, "is_baseline"))
        and str(_get(version, "kind")) == "initial"
    ]
    if len(baselines) != 1:
        raise InvariantError("version history must contain exactly one immutable baseline")

    extra_baselines = [version for version in versions if bool(_get(version, "is_baseline"))]
    if len(extra_baselines) != 1:
        raise InvariantError("only the initial version may be baseline")


def assert_export_structure(zip_data: bytes | str | Path) -> None:
    archive_input: str | Path | io.BytesIO
    if isinstance(zip_data, bytes):
        archive_input = io.BytesIO(zip_data)
    else:
        archive_input = zip_data

    with zipfile.ZipFile(archive_input) as archive:
        names = set(archive.namelist())
        required = {"note.md", "metadata.json"}
        missing = required - names
        if missing:
            raise InvariantError(f"export missing required entries: {sorted(missing)}")

        note = archive.read("note.md").decode("utf-8")
        image_refs = re.findall(r"\]\((images/[^)]+)\)", note)
        image_names = {name for name in names if name.startswith("images/")}
        if not image_refs:
            raise InvariantError("export note must reference at least one image")
        for ref in image_refs:
            if ref not in image_names:
                raise InvariantError(f"export image reference does not resolve: {ref}")
            if not re.match(r"images/\d{4}-[^/]+\.png$", ref):
                raise InvariantError(f"export image name has invalid format: {ref}")

        metadata = json.loads(archive.read("metadata.json").decode("utf-8"))
        clip_count = len(metadata.get("clips", []))
        if clip_count and len(image_names) != clip_count:
            raise InvariantError("export must contain one image per clip")


def assert_style_profile_valid(profile: dict[str, Any]) -> None:
    required = {"style_descriptor", "granularity", "density", "derived_prompt", "extracted_from"}
    missing = required - set(profile)
    if missing:
        raise InvariantError(f"style_profile missing required keys: {sorted(missing)}")

    for dimension in ("granularity", "density"):
        value = profile[dimension]
        if not isinstance(value, dict):
            raise InvariantError(f"style_profile.{dimension} must be an object")
        if value.get("source") not in {"examples", "depth"}:
            raise InvariantError(f"style_profile.{dimension}.source is invalid")


def assert_reconciliation_flags(note: dict[str, Any], op: str) -> None:
    expected = {
        "clip_change_polished": {"is_polished": True, "clips_dirty": True},
        "auto_sync": {"is_polished": False, "clips_dirty": False},
        "rebuild": {"is_polished": False, "clips_dirty": False},
        "keep": {"is_polished": True, "clips_dirty": False},
        "restore": {"clips_dirty": False},
    }
    if op not in expected:
        raise InvariantError(f"unknown reconciliation op: {op}")

    for key, value in expected[op].items():
        if note.get(key) is not value:
            raise InvariantError(f"reconciliation flags invalid for {op}: {key}")


def assert_note_content_flags(note: dict[str, Any]) -> None:
    if not (note.get("include_summary") or note.get("include_transcript")):
        raise InvariantError("include_summary or include_transcript must be true")
