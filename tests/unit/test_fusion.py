from __future__ import annotations

from vtn_core.settings import SegmentationSettings
from vtn_segment.detectors import BoundaryCandidate
from vtn_segment.fusion import fuse_boundaries


def test_fusion_clusters_scores_and_snaps_boundaries() -> None:
    settings = SegmentationSettings(
        merge_window_sec=4.0,
        min_score=0.5,
        weights={"slide_change": 0.7, "semantic_shift": 0.6, "time_gap": 0.2},
    )

    fused = fuse_boundaries(
        [
            BoundaryCandidate(9.0, "slide_change", 0.8, {}),
            BoundaryCandidate(11.0, "semantic_shift", 0.75, {}),
            BoundaryCandidate(23.0, "time_gap", 0.2, {}),
        ],
        transcript_starts=[0.0, 10.0, 14.0, 22.0],
        slide_times=[9.0, 14.0],
        settings=settings,
    )

    assert len(fused) == 1
    assert fused[0].at_sec == 9.0
    assert fused[0].signal_types == {"slide_change", "semantic_shift"}
    assert round(fused[0].score, 2) == 1.01
