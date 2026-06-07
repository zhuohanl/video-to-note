from __future__ import annotations

import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPIKE_OUT = ROOT / ".spike-out"


def ensure_out_dir(name: str) -> Path:
    path = SPIKE_OUT / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def ffmpeg_path() -> str:
    configured = os.environ.get("VTN_FFMPEG_PATH")
    if configured and Path(configured).exists():
        return configured

    found = shutil.which("ffmpeg")
    if found:
        return found

    winget_root = Path.home() / "AppData/Local/Microsoft/WinGet/Packages"
    matches = sorted(winget_root.glob("Gyan.FFmpeg_*/ffmpeg-*/bin/ffmpeg.exe"))
    if matches:
        return str(matches[-1])

    msg = "ffmpeg not found; install it or set VTN_FFMPEG_PATH"
    raise RuntimeError(msg)


def require_real() -> bool:
    if os.environ.get("RUN_REAL") != "1":
        print("SKIP: set RUN_REAL=1 to run this live external-service spike")
        return False
    return True


def require_env(*names: str) -> dict[str, str]:
    values = {name: os.environ.get(name, "") for name in names}
    missing = [name for name, value in values.items() if not value]
    if missing:
        msg = "Missing required env vars: " + ", ".join(missing)
        raise RuntimeError(msg)
    return values
