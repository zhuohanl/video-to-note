from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import imageio_ffmpeg  # type: ignore[import-untyped]


@dataclass(frozen=True)
class FrameSample:
    path: Path
    at_sec: Decimal


def ffmpeg_exe() -> str:
    return os.environ.get("FFMPEG_LOCATION") or imageio_ffmpeg.get_ffmpeg_exe()


def generate_test_video(path: Path, *, duration_sec: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            ffmpeg_exe(),
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc=duration={duration_sec}:size=320x180:rate=10",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )


class FfmpegFrameSampler:
    def __init__(self, *, output_dir: Path, fps: int = 1) -> None:
        self.output_dir = output_dir
        self.fps = fps

    def sample(self, video_path: Path) -> list[FrameSample]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        pattern = self.output_dir / "frame-%03d.png"
        subprocess.run(
            [
                ffmpeg_exe(),
                "-y",
                "-i",
                str(video_path),
                "-vf",
                f"fps={self.fps}",
                str(pattern),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return [
            FrameSample(path=path, at_sec=Decimal(index - 1).quantize(Decimal("0.001")))
            for index, path in enumerate(sorted(self.output_dir.glob("frame-*.png")), start=1)
        ]
