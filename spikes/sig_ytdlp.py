from __future__ import annotations

import json

import yt_dlp


def main() -> int:
    print(json.dumps({"yt_dlp_version": yt_dlp.version.__version__}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
