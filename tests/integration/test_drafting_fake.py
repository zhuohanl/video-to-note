from __future__ import annotations

import os
import subprocess
from uuid import UUID

import psycopg
import pytest
from vtn_core.models import PromptDepth
from vtn_storage.repos import JobRepository
from vtn_worker.runner import StageContext
from vtn_worker.stages.acquiring_media import acquire_media
from vtn_worker.stages.drafting import draft
from vtn_worker.stages.index_visual import index_visual
from vtn_worker.stages.resolving import resolve_job
from vtn_worker.stages.segmenting import segment
from vtn_worker.stages.transcribe import transcribe


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


async def _prepare_segmented_job(repo: JobRepository) -> UUID:
    job_id = _create_job(repo)
    await resolve_job(StageContext(job_id=job_id, attempt=0, stage="resolving", repo=repo))
    await acquire_media(StageContext(job_id=job_id, attempt=0, stage="acquiring_media", repo=repo))
    context = StageContext(job_id=job_id, attempt=0, stage="analyzing", repo=repo)
    await transcribe(context)
    await index_visual(context)
    await segment(StageContext(job_id=job_id, attempt=0, stage="segmenting", repo=repo))
    return job_id


@pytest.mark.asyncio
async def test_fake_drafting_marks_every_clip_ready_with_scene_and_clip_ready_event() -> None:
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    repo = JobRepository(_database_url())
    job_id = await _prepare_segmented_job(repo)

    await draft(StageContext(job_id=job_id, attempt=0, stage="drafting", repo=repo))

    with psycopg.connect(_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT order_index, status, scene_at_sec, scene_blob_path, scene_source,
                       summary, ai_summary
                FROM clips
                WHERE job_id = %s
                ORDER BY order_index
                """,
                (job_id,),
            )
            clips = cursor.fetchall()

    assert len(clips) == 2
    for (
        _order_index,
        status,
        scene_at_sec,
        scene_blob_path,
        scene_source,
        summary,
        ai_summary,
    ) in clips:
        assert status == "ready"
        assert scene_at_sec is not None
        assert scene_blob_path
        assert scene_source == "auto"
        assert "Outline: Introduction; Progress and export" in summary
        assert summary == ai_summary

    ready_events = [
        event for event in repo.list_events_after(job_id, 0) if event["type"] == "clip.ready"
    ]
    assert [event["payload"]["order_index"] for event in ready_events] == [0, 1]
