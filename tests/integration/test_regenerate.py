from __future__ import annotations

import os
import subprocess
from uuid import UUID

import psycopg
from fastapi import FastAPI
from fastapi.testclient import TestClient
from vtn_api.auth import sign_session
from vtn_api.errors import ApiError, api_error_handler
from vtn_api.routes.clips import router as clips_router
from vtn_api.routes.note import router as note_router
from vtn_core.invariants import assert_note_no_regen_marker, assert_reconciliation_flags
from vtn_core.models import PromptDepth
from vtn_notes.assemble import assemble_markdown
from vtn_storage.repos import JobRepository


def _database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", "postgresql://vtn:vtn@127.0.0.1:55432/vtn")


def _alembic(*args: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = _database_url()
    subprocess.run(["alembic", *args], check=True, env=env, capture_output=True, text=True)


def _headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {"cookie": f"vtn_session={sign_session('local')}"}
    if extra:
        headers.update(extra)
    return headers


def _app() -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(clips_router)
    app.include_router(note_router)
    return app


def _prepare_review_ready_job(repo: JobRepository) -> UUID:
    job_id = repo.create_submission(
        url="https://www.youtube.com/watch?v=demo",
        depth=PromptDepth.balanced,
        custom_prompt=None,
        examples=[],
        use_saved_style=False,
    ).job_id
    repo.replace_clips(
        job_id,
        [
            {
                "start_sec": "0.000",
                "end_sec": "5.000",
                "title": "Regenerate Me",
                "summary_seed": "Seed text",
                "summary": "Placeholder summary",
                "classification": "mixed",
                "confidence": 0.9,
            }
        ],
    )
    clip_id = repo.clip_rows(job_id)[0]["id"]
    repo.update_clip_draft(
        clip_id=clip_id,
        summary="Placeholder summary",
        scene_at_sec="1.000",
        scene_blob_path="frames/regenerate.png",
    )
    with psycopg.connect(_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE clips SET needs_regen = true WHERE id = %s", (clip_id,))
    clips = repo.drafted_clip_rows(job_id)
    repo.create_initial_note(job_id, assemble_markdown(clips), clips)
    repo.mark_review_ready(job_id)
    return job_id


def _set_polished(job_id: UUID) -> None:
    with psycopg.connect(_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE notes SET is_polished = true WHERE job_id = %s", (job_id,))


def _version_kinds(job_id: UUID) -> list[str]:
    with psycopg.connect(_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT kind FROM note_versions WHERE job_id = %s ORDER BY seq",
                (job_id,),
            )
            return [row[0] for row in cursor.fetchall()]


def test_regenerate_etag_autosync_marker_and_needs_ack(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", _database_url())
    monkeypatch.setenv("VTN_COOKIE_SECRET", "test-cookie-secret")
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    repo = JobRepository(_database_url())
    client = TestClient(_app())
    job_id = _prepare_review_ready_job(repo)
    clip = repo.clips_view(job_id)["clips"][0]

    stale = client.post(
        f"/clips/{clip['id']}/regenerate",
        headers=_headers({"if-match": '"stale"'}),
    )
    assert stale.status_code == 412
    assert stale.json()["error"]["code"] == "stale_write"

    regenerated = client.post(
        f"/clips/{clip['id']}/regenerate",
        headers=_headers({"if-match": clip["etag"]}),
    )
    assert regenerated.status_code == 200
    body = regenerated.json()
    assert body["needs_regen"] is False
    assert body["summary"] == "Regenerate Me: Seed text. Outline: Regenerate Me"
    assert body["summary"] != "Placeholder summary"
    note = client.get(f"/jobs/{job_id}/note", headers=_headers()).json()
    assert body["summary"] in note["markdown"]
    assert_note_no_regen_marker(note["markdown"])
    assert_reconciliation_flags(note, "auto_sync")

    with psycopg.connect(_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE clips SET needs_regen = true WHERE id = %s", (clip["id"],))
    _set_polished(job_id)
    polished_clip = repo.clips_view(job_id)["clips"][0]
    needs_ack = client.post(
        f"/clips/{polished_clip['id']}/regenerate",
        headers=_headers({"if-match": polished_clip["etag"]}),
    )
    assert needs_ack.status_code == 409
    assert needs_ack.json()["error"]["code"] == "needs_ack"

    acked = client.post(
        f"/clips/{polished_clip['id']}/regenerate?ack=1",
        headers=_headers({"if-match": polished_clip["etag"]}),
    )
    assert acked.status_code == 200
    assert acked.json()["needs_regen"] is False
    note_after_ack = client.get(f"/jobs/{job_id}/note", headers=_headers()).json()
    assert_reconciliation_flags(note_after_ack, "clip_change_polished")
    assert _version_kinds(job_id) == ["initial", "auto_pre_change"]
