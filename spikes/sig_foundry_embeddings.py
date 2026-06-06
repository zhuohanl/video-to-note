from __future__ import annotations

import json

from openai import __version__ as openai_version


def main() -> int:
    print(json.dumps({"openai_version": openai_version}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
