from __future__ import annotations

import json

import azure.servicebus


def main() -> int:
    print(json.dumps({"azure_servicebus": azure.servicebus.__version__}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
