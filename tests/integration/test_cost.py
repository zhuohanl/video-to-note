from __future__ import annotations

import os
import subprocess
from uuid import UUID

import pytest
from vtn_core.models import PromptDepth
from vtn_storage.queue import InMemoryQueue
from vtn_storage.repos import JobRepository
from vtn_worker.main import process_next
from vtn_worker.runner import StageContext
from vtn_worker.stages.resolving import resolve_job


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
async def test_cost_estimate_refinement_event_and_actuals_are_warn_only() -> None:
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    repo = JobRepository(_database_url())
    job_id = _create_job(repo)
    initial = repo.cost_row(job_id)
    assert initial["estimate_json"]["breakdown"]["profile"] == "submit_default"

    await resolve_job(StageContext(job_id, 0, "resolving", repo))

    events = repo.list_events_after(job_id, 0)
    assert events[-1]["type"] == "cost.estimate"
    refined = events[-1]["payload"]
    assert refined["breakdown"]["duration_sec"] == "30.000"
    assert repo.cost_row(job_id)["estimate_json"] == refined

    queue = InMemoryQueue()
    second_job = _create_job(repo)
    queue.send({"job_id": str(second_job), "attempt": 0})
    assert await process_next(queue, repo=repo)

    actuals = repo.cost_row(second_job)["actual_json"]
    assert actuals["tokens"] >= 0
    assert actuals["audio_min"] > 0
    assert actuals["ocr_frames"] > 0
    assert actuals["llm_calls"] > 0
