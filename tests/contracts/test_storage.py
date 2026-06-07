import os
import subprocess
from pathlib import Path

from vtn_core.models import JobStage, JobStatus, SourceType
from vtn_storage.blob import BlobStore, LocalBlobStore
from vtn_storage.queue import InMemoryQueue, QueueMessage, QueueProvider
from vtn_storage.repos import JobRepository


def _database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", "postgresql://vtn:vtn@127.0.0.1:55432/vtn")


def _alembic(*args: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = _database_url()
    subprocess.run(["alembic", *args], check=True, env=env, capture_output=True, text=True)


def test_in_memory_queue_round_trip_and_dead_letter() -> None:
    queue: QueueProvider = InMemoryQueue()

    message_id = queue.send({"job_id": "job-1", "attempt": 1})
    received = queue.receive()

    assert message_id == "mem-1"
    assert isinstance(received, QueueMessage)
    assert received.body == {"job_id": "job-1", "attempt": 1}

    queue.complete(received)
    assert queue.receive() is None

    queue.send({"job_id": "job-2", "attempt": 1})
    poison = queue.receive()
    assert poison is not None
    queue.dead_letter(poison, "boom")
    assert queue.dead_letters[0].reason == "boom"  # type: ignore[attr-defined]


def test_local_blob_store_put_get_url_and_delete_prefix(tmp_path: Path) -> None:
    blob: BlobStore = LocalBlobStore(tmp_path)

    url = blob.put("frames/job-1/0001.png", b"image-bytes")

    assert url == "local://frames/job-1/0001.png"
    assert blob.url_for("frames/job-1/0001.png") == url
    assert blob.get("frames/job-1/0001.png") == b"image-bytes"
    assert blob.delete_prefix("frames/job-1") == 1


def test_job_repository_insert_select_round_trip() -> None:
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")

    repo = JobRepository(_database_url())
    video_id = repo.create_video(
        source_url="https://youtu.be/demo",
        source_type=SourceType.youtube,
    )
    job_id = repo.create_job(video_id)
    job = repo.get_job(job_id)

    assert job is not None
    assert job.id == job_id
    assert job.video_id == video_id
    assert job.stage == JobStage.queued
    assert job.status == JobStatus.active

    _alembic("downgrade", "base")
