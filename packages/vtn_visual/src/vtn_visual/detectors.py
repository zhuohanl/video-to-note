from __future__ import annotations

from pathlib import Path
from typing import Protocol

from PIL import Image, ImageChops

from vtn_visual.index import VisualEventData
from vtn_visual.ocr import OcrFailure
from vtn_visual.phash import compute_phash
from vtn_visual.sampler import FfmpegFrameSampler


class OcrLike(Protocol):
    def extract_text(self, frame_path: str) -> str: ...


class VisualIndexer:
    def __init__(
        self,
        *,
        sampler: FfmpegFrameSampler,
        ocr: OcrLike,
        diff_threshold: float = 8.0,
    ) -> None:
        self.sampler = sampler
        self.ocr = ocr
        self.diff_threshold = diff_threshold

    def index(self, video_path: Path) -> tuple[list[VisualEventData], list[tuple[str, str]]]:
        samples = self.sampler.sample(video_path)
        events: list[VisualEventData] = []
        warnings: list[tuple[str, str]] = []
        previous_path: Path | None = None
        previous_text: str | None = None
        for sample in samples:
            phash = compute_phash(sample.path)
            ocr_text: str | None
            try:
                ocr_text = self.ocr.extract_text(str(sample.path))
            except OcrFailure as exc:
                ocr_text = None
                warnings.append(("ocr_failed", str(exc)))

            if previous_path is not None and _mean_pixel_delta(previous_path, sample.path) > (
                self.diff_threshold
            ):
                events.append(
                    VisualEventData(
                        sample.at_sec,
                        "slide_change",
                        0.8,
                        ocr_text,
                        phash,
                        str(sample.path),
                    )
                )
            if ocr_text and ocr_text != previous_text:
                events.append(
                    VisualEventData(
                        sample.at_sec,
                        "title_change",
                        0.85,
                        ocr_text,
                        phash,
                        str(sample.path),
                    )
                )
                previous_text = ocr_text

            events.append(
                VisualEventData(
                    sample.at_sec,
                    "keyframe",
                    0.75,
                    ocr_text,
                    phash,
                    str(sample.path),
                )
            )
            previous_path = sample.path
        return sorted(events, key=lambda event: (event.at_sec, event.event_type)), warnings


def _mean_pixel_delta(left: Path, right: Path) -> float:
    with Image.open(left) as left_image, Image.open(right) as right_image:
        diff = ImageChops.difference(left_image.convert("RGB"), right_image.convert("RGB"))
    histogram = diff.histogram()
    total = sum(value * (index % 256) for index, value in enumerate(histogram))
    pixels = left_image.width * left_image.height * 3
    return total / pixels
