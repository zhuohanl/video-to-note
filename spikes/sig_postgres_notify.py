from __future__ import annotations

import json

import asyncpg


def main() -> int:
    print(json.dumps({"asyncpg_version": asyncpg.__version__}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
