from __future__ import annotations

import os
from pathlib import Path

from fastapi import Request
from vtn_storage.blob import BlobStore, LocalBlobStore
from vtn_storage.queue import InMemoryQueue, QueueProvider
from vtn_storage.repos import JobRepository
from vtn_storage.servicebus import ServiceBusQueue


def database_url() -> str:
    return os.environ.get("DATABASE_URL", "postgresql://vtn:vtn@127.0.0.1:55432/vtn")


def job_repository() -> JobRepository:
    return JobRepository(database_url())


def queue_provider(request: Request) -> QueueProvider:
    queue = getattr(request.app.state, "queue", None)
    if queue is None:
        queue = _queue_from_env()
        request.app.state.queue = queue
    return queue


def blob_store(request: Request) -> BlobStore:
    store = getattr(request.app.state, "blob_store", None)
    if store is None:
        root = Path(os.environ.get("VTN_BLOB_ROOT", ".local/blob"))
        store = LocalBlobStore(root)
        request.app.state.blob_store = store
    return store


def _queue_from_env() -> QueueProvider:
    if os.environ.get("APP_PROFILE") == "azure" or os.environ.get(
        "AZURE_SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE",
    ):
        return ServiceBusQueue.from_env()
    return InMemoryQueue()
