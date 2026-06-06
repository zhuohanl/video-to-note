from __future__ import annotations

import asyncio
import os
from uuid import UUID

from vtn_storage.queue import InMemoryQueue, QueueProvider
from vtn_storage.repos import JobRepository

from vtn_worker.runner import PipelineError, StageHandlers, run


def _database_url() -> str:
    return os.environ.get("DATABASE_URL", "postgresql://vtn:vtn@127.0.0.1:55432/vtn")


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
        await run(job_id, attempt=message.attempt, repo=repository, stages=stages)
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
