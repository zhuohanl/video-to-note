from __future__ import annotations

import json

import imagehash
import PIL


def main() -> int:
    print(
        json.dumps(
            {
                "pillow_version": PIL.__version__,
                "imagehash_module": imagehash.__name__,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
