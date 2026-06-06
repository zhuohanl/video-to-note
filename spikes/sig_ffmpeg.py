from __future__ import annotations

import json
import subprocess

from common import ffmpeg_path


def main() -> int:
    completed = subprocess.run(
        [ffmpeg_path(), "-version"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    print(json.dumps({"ffmpeg": completed.stdout.splitlines()[0]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
