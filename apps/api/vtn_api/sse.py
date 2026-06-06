from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from uuid import UUID

import asyncpg  # type: ignore[import-untyped]
from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from vtn_storage.repos import JobRepository, event_channel

from vtn_api.auth import require_session
from vtn_api.deps import database_url, job_repository
from vtn_api.events import JobEventRow, to_sse

router = APIRouter()


async def _event_stream(
    repo: JobRepository,
    job_id: UUID,
    last_event_id: int,
) -> AsyncIterator[str]:
    current_id = last_event_id
    for row in repo.list_events_after(job_id, current_id):
        current_id = row["id"]
        yield to_sse(JobEventRow.model_validate(row))

    queue: asyncio.Queue[int] = asyncio.Queue()
    connection = await asyncpg.connect(database_url())
    channel = event_channel(job_id)

    def listener(
        connection: asyncpg.Connection,
        pid: int,
        channel: str,
        payload: str,
    ) -> None:
        del connection, pid, channel
        queue.put_nowait(int(payload))

    await connection.add_listener(channel, listener)
    try:
        while True:
            try:
                await asyncio.wait_for(queue.get(), timeout=15)
            except TimeoutError:
                yield ": heartbeat\n\n"
                continue

            for row in repo.list_events_after(job_id, current_id):
                current_id = row["id"]
                yield to_sse(JobEventRow.model_validate(row))
    finally:
        await connection.remove_listener(channel, listener)
        await connection.close()


@router.get("/jobs/{job_id}/events")
def job_events(
    job_id: UUID,
    last_event_id: int | None = Header(default=None, alias="Last-Event-ID"),
    session: str = Depends(require_session),
) -> StreamingResponse:
    del session
    return StreamingResponse(
        _event_stream(job_repository(), job_id, last_event_id or 0),
        media_type="text/event-stream",
    )
