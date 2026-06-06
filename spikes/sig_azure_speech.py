from __future__ import annotations

import json


def main() -> int:
    print(json.dumps({"sdk": "azure-cognitiveservices-speech", "status": "env-gated"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
