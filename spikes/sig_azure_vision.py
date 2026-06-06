from __future__ import annotations

import json


def main() -> int:
    print(
        json.dumps(
            {"sdk": "azure-ai-documentintelligence or vision REST", "status": "env-gated"},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
