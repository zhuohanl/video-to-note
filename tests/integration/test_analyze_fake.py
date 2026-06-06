from __future__ import annotations

import os
import subprocess
from uuid import UUID

import psycopg
import pytest
from vtn_core.models import PromptDepth, TranscriptSource
from vtn_storage.repos import JobRepository
from vtn_transcript.chain import FakeTranscriptProvider
from vtn_worker.runner import StageContext
from vtn_worker.stages.acquiring_media import acquire_media
from vtn_worker.stages.index_visual import index_visual
from vtn_worker.stages.resolving import resolve_job
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


def _counts(video_id: UUID) -> tuple[int, int]:
    with psycopg.connect(_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM transcript_spans WHERE video_id = %s", (video_id,))
            spans = int(cursor.fetchone()[0])
            cursor.execute("SELECT count(*) FROM visual_events WHERE video_id = %s", (video_id,))
            visuals = int(cursor.fetchone()[0])
    return spans, visuals


@pytest.mark.asyncio
async def test_fake_analyze_stages_write_artifacts_warning_and_rerun_idempotently() -> None:
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    repo = JobRepository(_database_url())
    job_id = _create_job(repo)
    context = StageContext(job_id=job_id, attempt=0, stage="analyzing", repo=repo)
    await resolve_job(StageContext(job_id=job_id, attempt=0, stage="resolving", repo=repo))
    video_id = repo.get_job_video_id(job_id)

    await acquire_media(StageContext(job_id=job_id, attempt=0, stage="acquiring_media", repo=repo))
    await transcribe(context, provider=FakeTranscriptProvider(force_asr_fallback=True))
    await index_visual(context)

    with psycopg.connect(_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT proxy_blob_path, proxy_state, transcript_state, visual_state
                FROM videos
                WHERE id = %s
                """,
                (video_id,),
            )
            video_row = cursor.fetchone()
            cursor.execute(
                """
                SELECT DISTINCT source
                FROM transcript_spans
                WHERE video_id = %s
                """,
                (video_id,),
            )
            transcript_sources = {row[0] for row in cursor.fetchall()}

    assert video_row == (f"proxy/{video_id}.mp4", "ready", "ready", "ready")
    assert transcript_sources == {TranscriptSource.azure_speech.value}
    assert _counts(video_id) == (5, 6)
    warnings = [event for event in repo.list_events_after(job_id, 0) if event["type"] == "warning"]
    assert warnings[-1]["payload"] == {
        "code": "asr_fallback",
        "message": "Using Azure Speech fallback",
    }

    await acquire_media(StageContext(job_id=job_id, attempt=0, stage="acquiring_media", repo=repo))
    await transcribe(context, provider=FakeTranscriptProvider(force_asr_fallback=True))
    await index_visual(context)

    assert _counts(video_id) == (5, 6)
