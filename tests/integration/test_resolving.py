from __future__ import annotations

import asyncio
import os
import subprocess
from uuid import UUID

import psycopg
import pytest
from vtn_core.models import PromptDepth
from vtn_storage.repos import JobRepository
from vtn_worker.runner import PipelineError, StageContext
from vtn_worker.stages.resolving import resolve_job


def _database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", "postgresql://vtn:vtn@127.0.0.1:55432/vtn")


def _alembic(*args: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = _database_url()
    subprocess.run(["alembic", *args], check=True, env=env, capture_output=True, text=True)


def _create_job(repo: JobRepository, url: str = "https://www.youtube.com/watch?v=demo") -> UUID:
    return repo.create_submission(
        url=url,
        depth=PromptDepth.balanced,
        custom_prompt=None,
        examples=[],
        use_saved_style=False,
    ).job_id


def _job_video_ids(job_ids: list[UUID]) -> list[UUID]:
    with psycopg.connect(_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT video_id
                FROM jobs
                WHERE id = ANY(%s)
                ORDER BY id
                """,
                (job_ids,),
            )
            return [row[0] for row in cursor.fetchall()]


def _video_count() -> int:
    with psycopg.connect(_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM videos")
            return int(cursor.fetchone()[0])


@pytest.mark.asyncio
async def test_resolving_promotes_one_canonical_video_under_concurrency() -> None:
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    repo = JobRepository(_database_url())
    job_ids = [_create_job(repo), _create_job(repo)]

    await asyncio.gather(
        *[
            resolve_job(StageContext(job_id=job_id, attempt=0, stage="resolving", repo=repo))
            for job_id in job_ids
        ]
    )

    video_ids = _job_video_ids(job_ids)
    assert len(set(video_ids)) == 1
    assert _video_count() == 1

    with psycopg.connect(_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT canonical_url, source_type, title, duration_sec
                FROM videos
                WHERE id = %s
                """,
                (video_ids[0],),
            )
            row = cursor.fetchone()

    assert row == (
        "https://www.youtube.com/watch?v=fake",
        "youtube",
        "Fake conference session",
        30,
    )


@pytest.mark.asyncio
async def test_resolving_surfaces_fake_validation_failures() -> None:
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    repo = JobRepository(_database_url())
    unsupported_job = _create_job(repo, "https://example.invalid/video")
    unavailable_job = _create_job(repo, "https://www.youtube.com/watch?v=unavailable")

    with pytest.raises(PipelineError) as unsupported:
        await resolve_job(
            StageContext(job_id=unsupported_job, attempt=0, stage="resolving", repo=repo)
        )
    with pytest.raises(PipelineError) as unavailable:
        await resolve_job(
            StageContext(job_id=unavailable_job, attempt=0, stage="resolving", repo=repo)
        )

    assert unsupported.value.code == "unsupported_url"
    assert unavailable.value.code == "video_unavailable"
