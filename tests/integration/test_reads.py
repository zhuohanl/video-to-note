from __future__ import annotations

import os
import subprocess
from uuid import UUID

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from vtn_api.auth import sign_session
from vtn_api.errors import ApiError, api_error_handler
from vtn_api.routes.clips import router as clips_router
from vtn_api.routes.note import router as note_router
from vtn_core.models import PromptDepth
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


def _app() -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(clips_router)
    app.include_router(note_router)
    return app


def _headers() -> dict[str, str]:
    return {"cookie": f"vtn_session={sign_session('local')}"}


def _create_job(repo: JobRepository) -> UUID:
    return repo.create_submission(
        url="https://www.youtube.com/watch?v=demo",
        depth=PromptDepth.balanced,
        custom_prompt=None,
        examples=[],
        use_saved_style=False,
    ).job_id


async def _prepare_review_ready_job(repo: JobRepository) -> UUID:
    job_id = _create_job(repo)
    await resolve_job(StageContext(job_id=job_id, attempt=0, stage="resolving", repo=repo))
    await acquire_media(StageContext(job_id=job_id, attempt=0, stage="acquiring_media", repo=repo))
    context = StageContext(job_id=job_id, attempt=0, stage="analyzing", repo=repo)
    await transcribe(context)
    await index_visual(context)
    await segment(StageContext(job_id=job_id, attempt=0, stage="segmenting", repo=repo))
    await draft(StageContext(job_id=job_id, attempt=0, stage="drafting", repo=repo))
    await assemble_initial_note(
        StageContext(job_id=job_id, attempt=0, stage="review_ready", repo=repo)
    )
    return job_id


def _expected_etags(job_id: UUID) -> tuple[list[str], str, str]:
    with psycopg.connect(_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT updated_at FROM clips WHERE job_id = %s ORDER BY order_index",
                (job_id,),
            )
            clip_etags = [f'"{row[0].isoformat()}"' for row in cursor.fetchall()]
            collection_etag = max(clip_etags)
            cursor.execute("SELECT updated_at FROM notes WHERE job_id = %s", (job_id,))
            note_etag = f'"{cursor.fetchone()[0].isoformat()}"'
    return clip_etags, collection_etag, note_etag


@pytest.mark.asyncio
async def test_read_endpoints_return_shapes_etags_and_require_cookie(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", _database_url())
    monkeypatch.setenv("VTN_COOKIE_SECRET", "test-cookie-secret")
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    repo = JobRepository(_database_url())
    job_id = await _prepare_review_ready_job(repo)
    clip_etags, collection_etag, note_etag = _expected_etags(job_id)
    client = TestClient(_app())

    assert client.get(f"/jobs/{job_id}/clips").status_code == 401
    assert client.get(f"/jobs/{job_id}/note").status_code == 401

    clips_response = client.get(f"/jobs/{job_id}/clips", headers=_headers())
    note_response = client.get(f"/jobs/{job_id}/note", headers=_headers())

    assert clips_response.status_code == 200
    clips = clips_response.json()
    assert clips["collection_etag"] == collection_etag
    assert [clip["etag"] for clip in clips["clips"]] == clip_etags
    assert [clip["order_index"] for clip in clips["clips"]] == [0, 1]
    assert all(clip["status"] == "ready" for clip in clips["clips"])
    assert all(clip["scene_url"].startswith("local://") for clip in clips["clips"])

    assert note_response.status_code == 200
    note = note_response.json()
    assert note["etag"] == note_etag
    assert note["include_summary"] is True
    assert note["include_transcript"] is False
    assert note["is_polished"] is False
    assert note["clips_dirty"] is False
    assert "## 1. Introduction" in note["markdown"]
