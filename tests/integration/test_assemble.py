from __future__ import annotations

import os
import subprocess
from uuid import UUID

import psycopg
import pytest
from vtn_core.invariants import (
    assert_baseline_immutable,
    assert_note_content_flags,
    assert_note_no_regen_marker,
    assert_note_no_transcript,
)
from vtn_core.models import JobStatus, PromptDepth
from vtn_storage.repos import JobRepository
from vtn_worker.runner import StageContext
from vtn_worker.stages.acquiring_media import acquire_media
from vtn_worker.stages.assemble import assemble_initial_note
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


async def _prepare_drafted_job(repo: JobRepository) -> UUID:
    job_id = _create_job(repo)
    await resolve_job(StageContext(job_id=job_id, attempt=0, stage="resolving", repo=repo))
    await acquire_media(StageContext(job_id=job_id, attempt=0, stage="acquiring_media", repo=repo))
    context = StageContext(job_id=job_id, attempt=0, stage="analyzing", repo=repo)
    await transcribe(context)
    await index_visual(context)
    await segment(StageContext(job_id=job_id, attempt=0, stage="segmenting", repo=repo))
    await draft(StageContext(job_id=job_id, attempt=0, stage="drafting", repo=repo))
    return job_id


@pytest.mark.asyncio
async def test_initial_note_assembly_writes_note_baseline_and_done_event() -> None:
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    repo = JobRepository(_database_url())
    job_id = await _prepare_drafted_job(repo)

    await assemble_initial_note(
        StageContext(job_id=job_id, attempt=0, stage="review_ready", repo=repo)
    )

    job = repo.get_job(job_id)
    assert job is not None
    assert job.status == JobStatus.review_ready

    with psycopg.connect(_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT markdown, include_summary, include_transcript,
                       is_polished, clips_dirty, built_from_version
                FROM notes
                WHERE job_id = %s
                """,
                (job_id,),
            )
            note = cursor.fetchone()
            cursor.execute(
                """
                SELECT seq, label, kind, is_baseline, note_markdown,
                       note_settings, clips_snapshot
                FROM note_versions
                WHERE job_id = %s
                """,
                (job_id,),
            )
            versions = cursor.fetchall()

    assert note is not None
    markdown = note[0]
    assert "## 1. Introduction" in markdown
    assert "![Introduction](images/0001-introduction.png)" in markdown
    assert "Outline: Introduction; Progress and export" in markdown
    assert note[1:] == (True, False, False, False, 1)
    assert_note_no_transcript(markdown)
    assert_note_no_regen_marker(markdown)
    assert_note_content_flags({"include_summary": note[1], "include_transcript": note[2]})

    assert len(versions) == 1
    assert_baseline_immutable(
        [{"seq": row[0], "kind": row[2], "is_baseline": row[3]} for row in versions]
    )
    assert versions[0][0:5] == (1, "v1", "initial", True, markdown)
    assert versions[0][5] == {
        "is_polished": False,
        "include_summary": True,
        "include_transcript": False,
    }
    assert len(versions[0][6]) == 2

    assert repo.list_events_after(job_id, 0)[-1]["type"] == "done"
