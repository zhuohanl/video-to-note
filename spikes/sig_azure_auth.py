from __future__ import annotations

import json
import shutil
import subprocess
import sys


def _run(command: list[str]) -> dict[str, object]:
    executable = shutil.which(command[0])
    if executable is None:
        return {"command": command, "available": False}

    completed = subprocess.run(
        [executable, *command[1:]],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return {
        "command": command,
        "available": True,
        "returncode": completed.returncode,
        "stdout": completed.stdout[:4000],
        "stderr": completed.stderr[:4000],
    }


def main() -> int:
    signature = {
        "python": sys.version,
        "az_version": _run(["az", "version"]),
        "az_account": _run(["az", "account", "show"]),
        "azd_version": _run(["azd", "version"]),
    }
    print(json.dumps(signature, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
