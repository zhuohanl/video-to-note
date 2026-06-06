from __future__ import annotations

import os

from fastapi import Request
from vtn_storage.queue import InMemoryQueue, QueueProvider
from vtn_storage.repos import JobRepository


def database_url() -> str:
    return os.environ.get("DATABASE_URL", "postgresql://vtn:vtn@127.0.0.1:55432/vtn")


def job_repository() -> JobRepository:
    return JobRepository(database_url())


def queue_provider(request: Request) -> QueueProvider:
    queue = getattr(request.app.state, "queue", None)
    if queue is None:
        queue = InMemoryQueue()
        request.app.state.queue = queue
    return queue
