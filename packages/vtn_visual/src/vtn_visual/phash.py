from __future__ import annotations

from pathlib import Path

import imagehash
from PIL import Image


def compute_phash(path: Path) -> str:
    with Image.open(path) as image:
        return str(imagehash.phash(image))


def hamming_distance(left: str, right: str) -> int:
    return bin(int(left, 16) ^ int(right, 16)).count("1")
