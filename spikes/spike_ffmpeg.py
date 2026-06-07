from __future__ import annotations

import json
import subprocess

from common import ensure_out_dir, ffmpeg_path


def _run(args: list[str]) -> None:
    subprocess.run(args, check=True, capture_output=True, text=True, timeout=60)


def main() -> int:
    out_dir = ensure_out_dir("ffmpeg")
    ffmpeg = ffmpeg_path()
    video = out_dir / "synthetic.mp4"
    frames = out_dir / "frame-%03d.png"
    exact = out_dir / "exact.png"

    _run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=3:size=320x180:rate=10",
            "-pix_fmt",
            "yuv420p",
            str(video),
        ]
    )
    _run([ffmpeg, "-y", "-i", str(video), "-vf", "fps=1", str(frames)])
    _run([ffmpeg, "-y", "-ss", "1.5", "-i", str(video), "-frames:v", "1", str(exact)])

    print(
        json.dumps(
            {
                "video": str(video),
                "coarse_frames": len(list(out_dir.glob("frame-*.png"))),
                "single_frame_exists": exact.exists(),
                "flags": ["-vf fps=1", "-ss <timestamp>", "-frames:v 1"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
