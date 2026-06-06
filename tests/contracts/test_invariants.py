import io
import json
import zipfile

import pytest
from vtn_core.invariants import (
    InvariantError,
    assert_baseline_immutable,
    assert_clips_contiguous_ordered,
    assert_export_structure,
    assert_note_content_flags,
    assert_note_no_regen_marker,
    assert_note_no_transcript,
    assert_reconciliation_flags,
    assert_style_profile_valid,
    assert_unique_order_index,
)

VALID_CLIPS = [
    {"order_index": 0, "start_sec": 0.0, "end_sec": 10.0},
    {"order_index": 1, "start_sec": 10.0, "end_sec": 20.0},
]


def test_note_markdown_invariants() -> None:
    assert_note_no_transcript("# Note\n\nBody")
    assert_note_no_regen_marker("# Note\n\nBody")

    with pytest.raises(InvariantError, match="transcript"):
        assert_note_no_transcript("# Note\n\n> leaked transcript")
    with pytest.raises(InvariantError, match="regeneration"):
        assert_note_no_regen_marker("## Needs regeneration: Intro")


def test_clip_order_invariants() -> None:
    assert_clips_contiguous_ordered(VALID_CLIPS)
    assert_unique_order_index(VALID_CLIPS)

    with pytest.raises(InvariantError, match="contiguous"):
        assert_clips_contiguous_ordered(
            [
                {"order_index": 0, "start_sec": 0, "end_sec": 10},
                {"order_index": 2, "start_sec": 10, "end_sec": 20},
            ]
        )
    with pytest.raises(InvariantError, match="overlap"):
        assert_clips_contiguous_ordered(
            [
                {"order_index": 0, "start_sec": 0, "end_sec": 10},
                {"order_index": 1, "start_sec": 9, "end_sec": 20},
            ]
        )
    with pytest.raises(InvariantError, match="Duplicate"):
        assert_unique_order_index(
            [
                {"order_index": 0, "start_sec": 0, "end_sec": 10},
                {"order_index": 0, "start_sec": 10, "end_sec": 20},
            ]
        )


def test_baseline_invariant() -> None:
    assert_baseline_immutable([{"seq": 1, "is_baseline": True, "kind": "initial"}])

    with pytest.raises(InvariantError, match="baseline"):
        assert_baseline_immutable(
            [
                {"seq": 1, "is_baseline": True, "kind": "initial"},
                {"seq": 2, "is_baseline": True, "kind": "manual"},
            ]
        )


def test_export_structure_invariant() -> None:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zip_file:
        zip_file.writestr("note.md", "![Intro](images/0001-intro.png)")
        zip_file.writestr("images/0001-intro.png", b"png")
        zip_file.writestr("metadata.json", json.dumps({"clips": [{"order_index": 0}]}))

    assert_export_structure(archive.getvalue())

    broken = io.BytesIO()
    with zipfile.ZipFile(broken, "w") as zip_file:
        zip_file.writestr("note.md", "![Intro](images/missing.png)")
        zip_file.writestr("metadata.json", "{}")

    with pytest.raises(InvariantError, match="image"):
        assert_export_structure(broken.getvalue())


def test_style_profile_invariant() -> None:
    profile = {
        "style_descriptor": "plain",
        "granularity": {"value": "medium", "confidence": 0.9, "source": "depth"},
        "density": {"value": "medium", "confidence": 0.8, "source": "examples"},
        "derived_prompt": "write concise notes",
        "extracted_from": [],
    }
    assert_style_profile_valid(profile)

    profile["density"]["source"] = "invalid"
    with pytest.raises(InvariantError, match="source"):
        assert_style_profile_valid(profile)


def test_reconciliation_and_content_flag_invariants() -> None:
    assert_reconciliation_flags({"is_polished": True, "clips_dirty": True}, "clip_change_polished")
    assert_reconciliation_flags({"is_polished": False, "clips_dirty": False}, "auto_sync")
    assert_note_content_flags({"include_summary": True, "include_transcript": False})

    with pytest.raises(InvariantError, match="reconciliation"):
        assert_reconciliation_flags({"is_polished": False, "clips_dirty": True}, "auto_sync")
    with pytest.raises(InvariantError, match="include_summary"):
        assert_note_content_flags({"include_summary": False, "include_transcript": False})
