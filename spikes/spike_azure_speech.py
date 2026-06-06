from __future__ import annotations

import json

from common import require_env, require_real


def main() -> int:
    if not require_real():
        return 0
    env = require_env("AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION", "VTN_SPIKE_AUDIO_PATH")
    print(
        json.dumps(
            {"speech_region": env["AZURE_SPEECH_REGION"], "span_shape": "start/end/text"},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
