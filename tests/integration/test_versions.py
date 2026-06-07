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
from vtn_api.routes.versions import router as versions_router
from vtn_core.invariants import assert_baseline_immutable, assert_reconciliation_flags
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


def _both_etags(note_etag: str, clips_etag: str) -> str:
    return f"{note_etag}, {clips_etag}"


def _app() -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(clips_router)
    app.include_router(note_router)
    app.include_router(versions_router)
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


def _version_rows(job_id: UUID) -> list[dict[str, object]]:
    with psycopg.connect(_database_url(), row_factory=psycopg.rows.dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT seq, label, kind, is_baseline, note_markdown, note_settings, clips_snapshot
                FROM note_versions
                WHERE job_id = %s
                ORDER BY seq
                """,
                (job_id,),
            )
            return list(cursor.fetchall())


def test_versions_save_restore_both_etags_and_non_destructive(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", _database_url())
    monkeypatch.setenv("VTN_COOKIE_SECRET", "test-cookie-secret")
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    repo = JobRepository(_database_url())
    client = TestClient(_app())
    job_id = _prepare_review_ready_job(repo)

    listed = client.get(f"/jobs/{job_id}/versions", headers=_headers())
    assert listed.status_code == 200
    assert listed.json()["versions"][0]["kind"] == "initial"

    note = client.get(f"/jobs/{job_id}/note", headers=_headers()).json()
    clips = client.get(f"/jobs/{job_id}/clips", headers=_headers()).json()
    stale_note_save = client.post(
        f"/jobs/{job_id}/versions",
        headers=_headers({"if-match": _both_etags('"stale"', clips["collection_etag"])}),
        json={"label": "bad"},
    )
    assert stale_note_save.status_code == 412
    stale_clips_save = client.post(
        f"/jobs/{job_id}/versions",
        headers=_headers({"if-match": _both_etags(note["etag"], '"stale"')}),
        json={"label": "bad"},
    )
    assert stale_clips_save.status_code == 412

    edited = client.put(
        f"/jobs/{job_id}/note",
        headers=_headers({"if-match": note["etag"]}),
        json={"markdown": "# Polished manual"},
    )
    assert edited.status_code == 200
    split = client.post(
        f"/clips/{clips['clips'][0]['id']}/split?ack=1",
        headers=_headers({"if-match": clips["collection_etag"]}),
        json={"at_sec": "5.000"},
    )
    assert split.status_code == 200
    dirty_note = client.get(f"/jobs/{job_id}/note", headers=_headers()).json()
    dirty_clips = client.get(f"/jobs/{job_id}/clips", headers=_headers()).json()
    assert_reconciliation_flags(dirty_note, "clip_change_polished")

    manual = client.post(
        f"/jobs/{job_id}/versions",
        headers=_headers(
            {"if-match": _both_etags(dirty_note["etag"], dirty_clips["collection_etag"])}
        ),
        json={"label": "drifted"},
    )
    assert manual.status_code == 200
    assert manual.json()["kind"] == "manual"
    assert manual.json()["seq"] == 4
    assert manual.json()["label"] == "drifted"
    after_manual_note = client.get(f"/jobs/{job_id}/note", headers=_headers()).json()
    after_manual_clips = client.get(f"/jobs/{job_id}/clips", headers=_headers()).json()
    assert after_manual_note["etag"] == dirty_note["etag"]
    assert after_manual_clips["collection_etag"] == dirty_clips["collection_etag"]

    rebuilt = client.post(
        f"/jobs/{job_id}/note/rebuild",
        headers=_headers({"if-match": dirty_note["etag"]}),
    )
    assert rebuilt.status_code == 200
    current_note = client.get(f"/jobs/{job_id}/note", headers=_headers()).json()
    current_clips = client.get(f"/jobs/{job_id}/clips", headers=_headers()).json()

    unknown = client.post(
        f"/jobs/{job_id}/versions/999/restore",
        headers=_headers(
            {"if-match": _both_etags(current_note["etag"], current_clips["collection_etag"])}
        ),
    )
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "version_not_found"

    stale_restore = client.post(
        f"/jobs/{job_id}/versions/4/restore",
        headers=_headers({"if-match": _both_etags(current_note["etag"], '"stale"')}),
    )
    assert stale_restore.status_code == 412

    restored = client.post(
        f"/jobs/{job_id}/versions/4/restore",
        headers=_headers(
            {"if-match": _both_etags(current_note["etag"], current_clips["collection_etag"])}
        ),
    )
    assert restored.status_code == 200
    restored_note = client.get(f"/jobs/{job_id}/note", headers=_headers()).json()
    restored_clips = client.get(f"/jobs/{job_id}/clips", headers=_headers()).json()
    assert restored_note["markdown"] == "# Polished manual"
    assert restored_note["is_polished"] is True
    assert restored_note["clips_dirty"] is False
    assert restored_clips["clips"][1]["title"] == "Intro (cont.)"

    rows = _version_rows(job_id)
    assert [row["kind"] for row in rows] == [
        "initial",
        "auto_edit",
        "auto_pre_change",
        "manual",
        "auto_rebuild",
        "restore",
    ]
    assert rows[-1]["note_markdown"] == current_note["markdown"]
    assert_baseline_immutable(rows)

    undo_restore = client.post(
        f"/jobs/{job_id}/versions/6/restore",
        headers=_headers(
            {"if-match": _both_etags(restored_note["etag"], restored_clips["collection_etag"])}
        ),
    )
    assert undo_restore.status_code == 200
    undo_note = client.get(f"/jobs/{job_id}/note", headers=_headers()).json()
    assert undo_note["markdown"] == current_note["markdown"]
    assert undo_note["clips_dirty"] is False
