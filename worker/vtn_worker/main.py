from __future__ import annotations

import asyncio
import os
from uuid import UUID

from vtn_storage.queue import InMemoryQueue, QueueProvider
from vtn_storage.repos import JobRepository
from vtn_transcript.chain import FakeTranscriptProvider

from vtn_worker.runner import PipelineError, StageContext, StageHandlers, run
from vtn_worker.stages.acquiring_media import acquire_media
from vtn_worker.stages.assemble import assemble_initial_note
from vtn_worker.stages.drafting import draft
from vtn_worker.stages.extract_style import extract_style
from vtn_worker.stages.index_visual import index_visual
from vtn_worker.stages.resolving import resolve_job
from vtn_worker.stages.segmenting import segment
from vtn_worker.stages.transcribe import transcribe


def _database_url() -> str:
    return os.environ.get("DATABASE_URL", "postgresql://vtn:vtn@127.0.0.1:55432/vtn")


async def _transcribe_with_asr_fallback(context: StageContext) -> None:
    await transcribe(context, provider=FakeTranscriptProvider(force_asr_fallback=True))


def default_stage_handlers() -> StageHandlers:
    return StageHandlers(
        resolving=resolve_job,
        acquiring_media=acquire_media,
        transcribe=_transcribe_with_asr_fallback,
        index_visual=index_visual,
        extract_style=extract_style,
        segmenting=segment,
        drafting=draft,
        assemble=assemble_initial_note,
    )


async def process_next(
    queue: QueueProvider,
    *,
    repo: JobRepository | None = None,
    stages: StageHandlers | None = None,
) -> bool:
    repository = repo or JobRepository(_database_url())
    message = queue.receive()
    if message is None:
        return False

    job_id = UUID(str(message.body["job_id"]))
    try:
        await run(
            job_id,
            attempt=message.attempt,
            repo=repository,
            stages=stages or default_stage_handlers(),
        )
    except PipelineError as exc:
        repository.fail_job(job_id, exc.code, exc.message)
        repository.emit_event(
            job_id,
            "error",
            {"code": exc.code, "message": exc.message, "stage": exc.stage},
        )
    finally:
        queue.complete(message)
    return True


async def run_loop(queue: QueueProvider) -> None:
    while await process_next(queue):
        continue


def main() -> None:
    asyncio.run(run_loop(InMemoryQueue()))


if __name__ == "__main__":
    main()
