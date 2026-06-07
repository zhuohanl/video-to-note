from __future__ import annotations

import json
import os

import yt_dlp
from common import ensure_out_dir, ffmpeg_path, require_real


def main() -> int:
    if not require_real():
        return 0

    url = os.environ.get("VTN_SPIKE_VIDEO_URL", "https://www.youtube.com/watch?v=BaW_jenozKc")
    out_dir = ensure_out_dir("ytdlp")
    output_template = str(out_dir / "proxy.%(ext)s")
    options = {
        "format": "bv*[height<=720]+ba/b[height<=720]/b",
        "outtmpl": output_template,
        "download_sections": ["*0-30"],
        "force_keyframes_at_cuts": True,
        "ffmpeg_location": ffmpeg_path(),
        "quiet": True,
        "noprogress": True,
    }

    with yt_dlp.YoutubeDL(options) as downloader:
        info = downloader.extract_info(url, download=True)

    print(
        json.dumps(
            {
                "id": info.get("id"),
                "duration": info.get("duration"),
                "extractor": info.get("extractor_key"),
                "requested_downloads": info.get("requested_downloads", []),
                "format_selector": options["format"],
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
