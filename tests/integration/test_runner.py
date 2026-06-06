from __future__ import annotations

import os
import subprocess
from uuid import UUID

import pytest
from vtn_core.models import JobStage, JobStatus, PromptDepth
from vtn_storage.queue import InMemoryQueue
from vtn_storage.repos import JobRepository
from vtn_worker.main import process_next
from vtn_worker.runner import PipelineError, StageContext, StageHandlers, run


def _database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", "postgresql://vtn:vtn@127.0.0.1:55432/vtn")


def _alembic(*args: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = _database_url()
    subprocess.run(["alembic", *args], check=True, env=env, capture_output=True, text=True)


def _create_job(repo: JobRepository) -> UUID:
    return repo.create_submission(
        url="https://www.youtube.com/watch?v=demo",
        depth=PromptDepth.balanced,
        custom_prompt=None,
        examples=[],
        use_saved_style=False,
    ).job_id


@pytest.mark.asyncio
async def test_runner_reaches_review_ready_and_keeps_parallel_stage_owner() -> None:
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    repo = JobRepository(_database_url())
    job_id = _create_job(repo)
    branch_observed_stages: list[JobStage] = []

    async def branch_probe(context: StageContext) -> None:
        job = context.repo.get_job(context.job_id)
        assert job is not None
        branch_observed_stages.append(job.stage)

    await run(
        job_id,
        attempt=0,
        repo=repo,
        stages=StageHandlers(
            transcribe=branch_probe,
            index_visual=branch_probe,
            extract_style=branch_probe,
        ),
    )

    job = repo.get_job(job_id)
    assert job is not None
    assert job.status == JobStatus.review_ready
    assert job.stage == JobStage.drafting
    assert branch_observed_stages == [JobStage.analyzing, JobStage.analyzing, JobStage.analyzing]

    events = repo.list_events_after(job_id, 0)
    assert [(event["type"], event["payload"]) for event in events] == [
        ("stage", {"stage": "resolving"}),
        ("stage", {"stage": "acquiring_media"}),
        ("stage", {"stage": "analyzing"}),
        ("stage", {"stage": "transcribe"}),
        ("stage", {"stage": "index visual"}),
        ("stage", {"stage": "extract style"}),
        ("stage", {"stage": "segmenting"}),
        ("stage", {"stage": "drafting"}),
        ("done", {}),
    ]


@pytest.mark.asyncio
async def test_runner_skips_duplicate_delivery_after_review_ready() -> None:
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    repo = JobRepository(_database_url())
    job_id = _create_job(repo)
    calls: list[str] = []

    async def record(context: StageContext) -> None:
        calls.append(context.stage)

    stages = StageHandlers(
        resolving=record,
        acquiring_media=record,
        transcribe=record,
        index_visual=record,
        extract_style=record,
        segmenting=record,
        drafting=record,
    )

    await run(job_id, attempt=0, repo=repo, stages=stages)
    first_events = repo.list_events_after(job_id, 0)

    await run(job_id, attempt=1, repo=repo, stages=stages)

    assert calls == [
        "resolving",
        "acquiring_media",
        "transcribe",
        "index visual",
        "extract style",
        "segmenting",
        "drafting",
    ]
    assert repo.list_events_after(job_id, 0) == first_events


@pytest.mark.asyncio
async def test_worker_process_next_records_failure_event_and_completes_message() -> None:
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    repo = JobRepository(_database_url())
    job_id = _create_job(repo)
    queue = InMemoryQueue()
    queue.send({"job_id": str(job_id), "attempt": 1})

    async def fail_resolving(context: StageContext) -> None:
        raise PipelineError("video_unavailable", "Video is unavailable", context.stage)

    await process_next(
        queue,
        repo=repo,
        stages=StageHandlers(resolving=fail_resolving),
    )

    assert queue.receive() is None
    job = repo.get_job(job_id)
    assert job is not None
    assert job.status == JobStatus.failed
    assert job.error_code == "video_unavailable"
    assert job.error_message == "Video is unavailable"

    events = repo.list_events_after(job_id, 0)
    assert events[-1]["type"] == "error"
    assert events[-1]["payload"] == {
        "code": "video_unavailable",
        "message": "Video is unavailable",
        "stage": "resolving",
    }
