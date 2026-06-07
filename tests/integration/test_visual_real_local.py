from __future__ import annotations

from pathlib import Path

from vtn_visual.detectors import VisualIndexer
from vtn_visual.ocr import FakeOcrProvider
from vtn_visual.sampler import FfmpegFrameSampler, generate_test_video


def test_ffmpeg_visual_indexer_produces_phash_events_with_fake_ocr(tmp_path) -> None:
    video = tmp_path / "synthetic.mp4"
    generate_test_video(video, duration_sec=3)
    sampler = FfmpegFrameSampler(output_dir=tmp_path / "frames")
    ocr = FakeOcrProvider(
        {
            "frame-001.png": "Intro",
            "frame-002.png": "Architecture",
            "frame-003.png": "Demo",
        }
    )

    events, warnings = VisualIndexer(sampler=sampler, ocr=ocr).index(video)

    assert warnings == []
    assert len(events) >= 3
    assert all(event.phash and len(event.phash) == 16 for event in events)
    assert {event.event_type for event in events} >= {"keyframe", "title_change"}
    assert [event.at_sec for event in events] == sorted(event.at_sec for event in events)


def test_visual_indexer_ocr_failure_is_non_blocking_warning(tmp_path) -> None:
    video = tmp_path / "synthetic.mp4"
    generate_test_video(video, duration_sec=2)

    events, warnings = VisualIndexer(
        sampler=FfmpegFrameSampler(output_dir=tmp_path / "frames"),
        ocr=FakeOcrProvider({}, fail_for={Path("frame-001.png").name}),
    ).index(video)

    assert events
    assert warnings == [("ocr_failed", "OCR failed for frame-001.png")]
