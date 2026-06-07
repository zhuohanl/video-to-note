from __future__ import annotations

import json

from common import require_env, require_real


def main() -> int:
    if not require_real():
        return 0
    env = require_env("AZURE_VISION_ENDPOINT", "AZURE_VISION_KEY", "VTN_SPIKE_FRAME_PATH")
    print(
        json.dumps(
            {"vision_endpoint": env["AZURE_VISION_ENDPOINT"], "ocr_shape": "text+bbox"},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
