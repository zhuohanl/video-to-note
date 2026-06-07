from __future__ import annotations

from decimal import Decimal

from vtn_notes.scene import SceneCandidate, choose_scene


def test_scene_scoring_deduplicates_phash_and_prefers_best_visual_frame() -> None:
    chosen = choose_scene(
        [
            SceneCandidate(Decimal("1.000"), "speaker", 0.9, "aaaa", "frames/1.png"),
            SceneCandidate(Decimal("5.000"), "slide", 0.7, "bbbb", "frames/2.png"),
            SceneCandidate(Decimal("6.000"), "slide", 0.95, "bbba", "frames/3.png"),
            SceneCandidate(Decimal("9.000"), "demo", 0.8, "cccc", "frames/4.png"),
        ]
    )

    assert chosen.at_sec == Decimal("9.000")
    assert chosen.frame_blob_path == "frames/4.png"
