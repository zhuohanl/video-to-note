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
from vtn_core.invariants import assert_reconciliation_flags
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
                "end_sec": "10.000",
                "title": "Intro",
                "summary_seed": "Seed",
                "summary": "Original summary",
                "classification": "mixed",
                "confidence": 0.9,
            }
        ],
    )
    clip_id = repo.clip_rows(job_id)[0]["id"]
    repo.update_clip_draft(
        clip_id=clip_id,
        summary="Original summary",
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


def _built_from_version(job_id: UUID) -> int | None:
    with psycopg.connect(_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT built_from_version FROM notes WHERE job_id = %s", (job_id,))
            row = cursor.fetchone()
            return row[0] if row is not None else None


def test_rebuild_keep_and_worked_example_version_flow(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", _database_url())
    monkeypatch.setenv("VTN_COOKIE_SECRET", "test-cookie-secret")
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    repo = JobRepository(_database_url())
    client = TestClient(_app())
    job_id = _prepare_review_ready_job(repo)

    initial = client.get(f"/jobs/{job_id}/note", headers=_headers()).json()
    edited = client.put(
        f"/jobs/{job_id}/note",
        headers=_headers({"if-match": initial["etag"]}),
        json={"markdown": "# Polished note"},
    )
    assert edited.status_code == 200
    assert_reconciliation_flags(edited.json(), "keep")
    assert _versions(job_id) == [
        (1, "initial", initial["markdown"]),
        (2, "auto_edit", "# Polished note"),
    ]

    clip_view = repo.clips_view(job_id)
    split = client.post(
        f"/clips/{clip_view['clips'][0]['id']}/split?ack=1",
        headers=_headers({"if-match": clip_view["collection_etag"]}),
        json={"at_sec": "5.000"},
    )
    assert split.status_code == 200
    dirty = client.get(f"/jobs/{job_id}/note", headers=_headers()).json()
    assert dirty["markdown"] == "# Polished note"
    assert_reconciliation_flags(dirty, "clip_change_polished")
    assert _versions(job_id) == [
        (1, "initial", initial["markdown"]),
        (2, "auto_edit", "# Polished note"),
        (3, "auto_pre_change", "# Polished note"),
    ]

    stale_rebuild = client.post(
        f"/jobs/{job_id}/note/rebuild",
        headers=_headers({"if-match": edited.json()["etag"]}),
    )
    assert stale_rebuild.status_code == 412
    assert stale_rebuild.json()["error"]["code"] == "stale_write"

    rebuilt = client.post(
        f"/jobs/{job_id}/note/rebuild",
        headers=_headers({"if-match": dirty["etag"]}),
    )
    assert rebuilt.status_code == 200
    body = rebuilt.json()
    assert "Original summary" in body["markdown"]
    assert "Intro (cont.)" in body["markdown"]
    assert_reconciliation_flags(body, "rebuild")
    assert _versions(job_id) == [
        (1, "initial", initial["markdown"]),
        (2, "auto_edit", "# Polished note"),
        (3, "auto_pre_change", "# Polished note"),
        (4, "auto_rebuild", body["markdown"]),
    ]
    assert _built_from_version(job_id) == 4

    keep_job_id = _prepare_review_ready_job(repo)
    keep_initial = client.get(f"/jobs/{keep_job_id}/note", headers=_headers()).json()
    keep_edited = client.put(
        f"/jobs/{keep_job_id}/note",
        headers=_headers({"if-match": keep_initial["etag"]}),
        json={"markdown": "# Keep my note"},
    )
    keep_clip_view = repo.clips_view(keep_job_id)
    keep_split = client.post(
        f"/clips/{keep_clip_view['clips'][0]['id']}/split?ack=1",
        headers=_headers({"if-match": keep_clip_view["collection_etag"]}),
        json={"at_sec": "5.000"},
    )
    assert keep_split.status_code == 200
    keep_dirty = client.get(f"/jobs/{keep_job_id}/note", headers=_headers()).json()
    assert_reconciliation_flags(keep_dirty, "clip_change_polished")

    stale_keep = client.post(
        f"/jobs/{keep_job_id}/note/keep",
        headers=_headers({"if-match": keep_edited.json()["etag"]}),
    )
    assert stale_keep.status_code == 412

    kept = client.post(
        f"/jobs/{keep_job_id}/note/keep",
        headers=_headers({"if-match": keep_dirty["etag"]}),
    )
    assert kept.status_code == 200
    assert kept.json()["markdown"] == "# Keep my note"
    assert_reconciliation_flags(kept.json(), "keep")
