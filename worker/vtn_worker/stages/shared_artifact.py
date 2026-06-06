from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import timedelta
from uuid import UUID

from vtn_core.settings import ArtifactSettings
from vtn_storage.repos import ArtifactKind

from vtn_worker.runner import StageContext

BuildFn = Callable[[], Awaitable[None]]


async def run_video_artifact(
    context: StageContext,
    video_id: UUID,
    artifact: ArtifactKind,
    build: BuildFn,
    *,
    settings: ArtifactSettings | None = None,
) -> bool:
    artifact_settings = settings or ArtifactSettings()
    stale_after = timedelta(seconds=artifact_settings.stale_timeout_sec)

    claimed = await asyncio.to_thread(
        context.repo.claim_artifact,
        video_id,
        context.job_id,
        artifact,
    )
    if not claimed:
        claimed = await asyncio.to_thread(
            context.repo.reclaim_stale,
            video_id,
            context.job_id,
            artifact,
            stale_after=stale_after,
        )

    if not claimed:
        ready = await asyncio.to_thread(
            context.repo.wait_ready,
            video_id,
            artifact,
            timeout_sec=artifact_settings.wait_timeout_sec,
            poll_interval_sec=artifact_settings.poll_interval_sec,
        )
        if ready:
            return False
        claimed = await asyncio.to_thread(
            context.repo.claim_artifact,
            video_id,
            context.job_id,
            artifact,
        )
        if not claimed:
            raise TimeoutError(f"{artifact} artifact did not become ready")

    try:
        await build()
        return True
    except Exception:
        await asyncio.to_thread(
            context.repo.release_on_fail,
            video_id,
            context.job_id,
            artifact,
        )
        raise
