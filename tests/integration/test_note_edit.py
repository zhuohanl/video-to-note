from __future__ import annotations

import os
import subprocess
from uuid import UUID

import psycopg
from fastapi import FastAPI
from fastapi.testclient import TestClient
from vtn_api.auth import sign_session
from vtn_api.errors import ApiError, api_error_handler
from vtn_api.routes.note import router as note_router
from vtn_core.invariants import assert_note_content_flags, assert_note_no_transcript
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
                "title": "Intro",
                "summary_seed": "Seed",
                "summary": "Summary",
                "classification": "mixed",
                "confidence": 0.9,
            }
        ],
    )
    clip_id = repo.clip_rows(job_id)[0]["id"]
    repo.update_clip_draft(
        clip_id=clip_id,
        summary="Summary",
        scene_at_sec="1.000",
        scene_blob_path="frames/intro.png",
    )
    clips = repo.drafted_clip_rows(job_id)
    repo.create_initial_note(job_id, assemble_markdown(clips), clips)
    repo.mark_review_ready(job_id)
    return job_id


def _versions(job_id: UUID) -> list[tuple[int, str, str]]:
    with psycopg.connect(_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT seq, kind, note_markdown
                FROM note_versions
                WHERE job_id = %s
                ORDER BY seq
                """,
                (job_id,),
            )
            return [(row[0], row[1], row[2]) for row in cursor.fetchall()]


def test_note_autosave_coalesces_and_content_flags_are_projections(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", _database_url())
    monkeypatch.setenv("VTN_COOKIE_SECRET", "test-cookie-secret")
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    repo = JobRepository(_database_url())
    client = TestClient(_app())
    job_id = _prepare_review_ready_job(repo)

    initial = client.get(f"/jobs/{job_id}/note", headers=_headers()).json()
    stale_put = client.put(
        f"/jobs/{job_id}/note",
        headers=_headers({"if-match": '"stale"'}),
        json={"markdown": "Edited"},
    )
    assert stale_put.status_code == 412
    assert stale_put.json()["error"]["code"] == "stale_write"

    first = client.put(
        f"/jobs/{job_id}/note",
        headers=_headers({"if-match": initial["etag"]}),
        json={"markdown": "# Edited 1"},
    )
    assert first.status_code == 200
    assert first.json()["is_polished"] is True
    second = client.put(
        f"/jobs/{job_id}/note",
        headers=_headers({"if-match": first.json()["etag"]}),
        json={"markdown": "# Edited 2"},
    )
    assert second.status_code == 200
    assert second.json()["markdown"] == "# Edited 2"
    assert _versions(job_id) == [
        (1, "initial", initial["markdown"]),
        (2, "auto_edit", "# Edited 2"),
    ]
    assert_note_no_transcript(second.json()["markdown"])
    assert_note_content_flags(second.json())

    stale_patch = client.patch(
        f"/jobs/{job_id}/note",
        headers=_headers({"if-match": first.json()["etag"]}),
        json={"include_transcript": True},
    )
    assert stale_patch.status_code == 412

    transcript_on = client.patch(
        f"/jobs/{job_id}/note",
        headers=_headers({"if-match": second.json()["etag"]}),
        json={"include_transcript": True},
    )
    assert transcript_on.status_code == 200
    assert transcript_on.json()["markdown"] == "# Edited 2"
    assert transcript_on.json()["is_polished"] is True
    assert transcript_on.json()["include_summary"] is True
    assert transcript_on.json()["include_transcript"] is True
    assert_note_content_flags(transcript_on.json())

    summary_off = client.patch(
        f"/jobs/{job_id}/note",
        headers=_headers({"if-match": transcript_on.json()["etag"]}),
        json={"include_summary": False},
    )
    assert summary_off.status_code == 200
    assert summary_off.json()["markdown"] == "# Edited 2"
    assert summary_off.json()["is_polished"] is True
    assert summary_off.json()["include_summary"] is False
    assert summary_off.json()["include_transcript"] is True
    assert_note_content_flags(summary_off.json())

    both_false = client.patch(
        f"/jobs/{job_id}/note",
        headers=_headers({"if-match": summary_off.json()["etag"]}),
        json={"include_summary": False, "include_transcript": False},
    )
    assert both_false.status_code == 422
    assert both_false.json()["error"]["code"] == "validation_error"
    resultant_false = client.patch(
        f"/jobs/{job_id}/note",
        headers=_headers({"if-match": summary_off.json()["etag"]}),
        json={"include_transcript": False},
    )
    assert resultant_false.status_code == 422
    assert resultant_false.json()["error"]["code"] == "validation_error"
    after_reject = client.get(f"/jobs/{job_id}/note", headers=_headers()).json()
    assert after_reject["markdown"] == "# Edited 2"
    assert after_reject["include_summary"] is False
    assert after_reject["include_transcript"] is True
