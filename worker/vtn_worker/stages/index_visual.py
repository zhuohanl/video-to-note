from __future__ import annotations

import asyncio

from vtn_visual.index import FakeFrameSampler, FakeOcr

from vtn_worker.runner import StageContext
from vtn_worker.stages.shared_artifact import run_video_artifact


async def index_visual(
    context: StageContext,
    sampler: FakeFrameSampler | None = None,
    ocr: FakeOcr | None = None,
) -> None:
    frame_sampler = sampler or FakeFrameSampler()
    ocr_provider = ocr or FakeOcr()
    video_id = context.repo.get_job_video_id(context.job_id)

    async def build() -> None:
        rows = []
        for event in frame_sampler.sample(video_id):
            ocr_text = event.ocr_text
            if not ocr_text and event.frame_blob_path:
                ocr_text = ocr_provider.extract_text(event.frame_blob_path)
            rows.append(
                {
                    "at_sec": event.at_sec,
                    "event_type": event.event_type,
                    "confidence": event.confidence,
                    "ocr_text": ocr_text,
                    "phash": event.phash,
                    "frame_blob_path": event.frame_blob_path,
                }
            )

        await asyncio.to_thread(context.repo.replace_visual_events, video_id, rows)

    if context.repo.visual_event_rows(video_id):
        return

    await run_video_artifact(context, video_id, "visual", build)
