from __future__ import annotations

import asyncio

from vtn_ingest.acquire import FakeAcquirer

from vtn_worker.runner import StageContext


async def acquire_media(context: StageContext, acquirer: FakeAcquirer | None = None) -> None:
    media_acquirer = acquirer or FakeAcquirer()
    video_id = context.repo.get_job_video_id(context.job_id)
    if context.repo.proxy_blob_path(video_id):
        return

    artifact = media_acquirer.download_proxy(video_id)
    await asyncio.to_thread(context.repo.set_proxy_ready, video_id, artifact.blob_path)
