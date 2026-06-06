from __future__ import annotations

import json

import imagehash
from common import ensure_out_dir
from PIL import Image, ImageDraw


def main() -> int:
    out_dir = ensure_out_dir("phash")
    base = Image.new("RGB", (256, 144), "white")
    draw = ImageDraw.Draw(base)
    draw.rectangle((20, 20, 220, 90), outline="black", width=4)
    draw.text((30, 45), "Architecture", fill="black")

    near = base.copy()
    ImageDraw.Draw(near).text((30, 70), "v2", fill="gray")
    different = Image.new("RGB", (256, 144), "navy")
    ImageDraw.Draw(different).ellipse((60, 20, 190, 120), fill="gold")

    paths = [out_dir / "base.png", out_dir / "near.png", out_dir / "different.png"]
    for image, path in zip([base, near, different], paths, strict=True):
        image.save(path)

    hashes = [imagehash.phash(Image.open(path)) for path in paths]
    near_distance = int(hashes[0] - hashes[1])
    different_distance = int(hashes[0] - hashes[2])

    print(
        json.dumps(
            {
                "hash_size_bits": len(str(hashes[0])) * 4,
                "near_distance": near_distance,
                "different_distance": different_distance,
                "suggested_duplicate_threshold": 8,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
