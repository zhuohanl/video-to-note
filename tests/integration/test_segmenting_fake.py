from __future__ import annotations

import os
import subprocess
from uuid import UUID

import psycopg
import pytest
from vtn_core.invariants import assert_clips_contiguous_ordered, assert_unique_order_index
from vtn_core.models import PromptDepth
from vtn_segment.refine import FakeRefiner
from vtn_storage.repos import JobRepository
from vtn_worker.runner import StageContext
from vtn_worker.stages.acquiring_media import acquire_media
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


async def _prepare_analyzed_job(repo: JobRepository) -> UUID:
    job_id = _create_job(repo)
    await resolve_job(StageContext(job_id=job_id, attempt=0, stage="resolving", repo=repo))
    await acquire_media(StageContext(job_id=job_id, attempt=0, stage="acquiring_media", repo=repo))
    context = StageContext(job_id=job_id, attempt=0, stage="analyzing", repo=repo)
    await transcribe(context)
    await index_visual(context)
    return job_id


def _clips(job_id: UUID) -> list[dict[str, object]]:
    with psycopg.connect(_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT order_index, start_sec, end_sec, title, summary_seed,
                       classification, status
                FROM clips
                WHERE job_id = %s
                ORDER BY order_index
                """,
                (job_id,),
            )
            return [
                {
                    "order_index": row[0],
                    "start_sec": row[1],
                    "end_sec": row[2],
                    "title": row[3],
                    "summary_seed": row[4],
                    "classification": row[5],
                    "status": row[6],
                }
                for row in cursor.fetchall()
            ]


@pytest.mark.asyncio
async def test_fake_segmenting_persists_contiguous_pending_clips() -> None:
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    repo = JobRepository(_database_url())
    job_id = await _prepare_analyzed_job(repo)

    await segment(StageContext(job_id=job_id, attempt=0, stage="segmenting", repo=repo))

    clips = _clips(job_id)
    assert_clips_contiguous_ordered(clips)
    assert_unique_order_index(clips)
    assert clips == [
        {
            "order_index": 0,
            "start_sec": 0,
            "end_sec": 14,
            "title": "Introduction",
            "summary_seed": "Opening architecture context",
            "classification": "mixed",
            "status": "pending",
        },
        {
            "order_index": 1,
            "start_sec": 14,
            "end_sec": 28,
            "title": "Progress and export",
            "summary_seed": "Worker progress reaches reviewed export",
            "classification": "visual_led",
            "status": "pending",
        },
    ]


@pytest.mark.asyncio
async def test_fake_segmenting_refinement_fallback_emits_warning() -> None:
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    repo = JobRepository(_database_url())
    job_id = await _prepare_analyzed_job(repo)

    await segment(
        StageContext(job_id=job_id, attempt=0, stage="segmenting", repo=repo),
        refiner=FakeRefiner(invalid_json=True),
    )

    assert len(_clips(job_id)) == 2
    warnings = [event for event in repo.list_events_after(job_id, 0) if event["type"] == "warning"]
    assert warnings[-1]["payload"] == {
        "code": "refinement_fallback",
        "message": "Using deterministic segment boundaries",
    }
