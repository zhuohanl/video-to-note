from __future__ import annotations

import json
import os
import subprocess
import zipfile
from io import BytesIO
from pathlib import Path
from uuid import UUID

import psycopg
from fastapi import FastAPI
from fastapi.testclient import TestClient
from vtn_api.auth import sign_session
from vtn_api.errors import ApiError, api_error_handler
from vtn_api.routes.clips import router as clips_router
from vtn_api.routes.export import router as export_router
from vtn_api.routes.jobs import router as jobs_router
from vtn_api.routes.note import router as note_router
from vtn_core.invariants import assert_export_structure, assert_note_no_regen_marker
from vtn_core.models import PromptDepth, TranscriptSource
from vtn_notes.assemble import assemble_markdown
from vtn_storage.blob import LocalBlobStore
from vtn_storage.repos import JobRepository

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?"
    b"\x00\x05\xfe\x02\xfeA\xe2!\xbc\x00\x00\x00\x00IEND\xaeB`\x82"
)


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


def _app(blob_store: LocalBlobStore) -> FastAPI:
    app = FastAPI()
    app.state.blob_store = blob_store
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(clips_router)
    app.include_router(jobs_router)
    app.include_router(note_router)
    app.include_router(export_router)
    return app


def _prepare_review_ready_job(repo: JobRepository, blob_store: LocalBlobStore) -> UUID:
    job_id = repo.create_submission(
        url="https://www.youtube.com/watch?v=demo",
        depth=PromptDepth.balanced,
        custom_prompt=None,
        examples=[],
        use_saved_style=False,
    ).job_id
    video_id = repo.get_job_video_id(job_id)
    repo.replace_transcript_spans(
        video_id,
        [
            {
                "start_sec": "0.000",
                "end_sec": "4.000",
                "text": "Transcript for intro.",
                "speaker": "Speaker",
            }
        ],
        TranscriptSource.azure_speech,
    )
    repo.replace_clips(
        job_id,
        [
            {
                "start_sec": "0.000",
                "end_sec": "4.000",
                "title": "Intro",
                "summary_seed": "Seed",
                "summary": "Original prose",
                "classification": "mixed",
                "confidence": 0.9,
            }
        ],
    )
    clip_id = repo.clip_rows(job_id)[0]["id"]
    blob_store.put("frames/intro.png", PNG_BYTES)
    repo.update_clip_draft(
        clip_id=clip_id,
        summary="Original prose",
        scene_at_sec="1.000",
        scene_blob_path="frames/intro.png",
    )
    with psycopg.connect(_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE clips SET scene_caption = 'Caption text' WHERE id = %s",
                (clip_id,),
            )
    clips = repo.drafted_clip_rows(job_id)
    repo.create_initial_note(job_id, assemble_markdown(clips), clips)
    repo.mark_review_ready(job_id)
    return job_id


def _download_zip(blob_store: LocalBlobStore, response_body: dict[str, str]) -> bytes:
    prefix = "local://"
    assert response_body["download_url"].startswith(prefix)
    return blob_store.get(response_body["download_url"][len(prefix) :])


def _note_from_zip(zip_bytes: bytes) -> str:
    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        return archive.read("note.md").decode("utf-8")


def _metadata_from_zip(zip_bytes: bytes) -> dict[str, object]:
    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        return json.loads(archive.read("metadata.json").decode("utf-8"))


def test_export_zip_projections_repeatable_and_non_locking(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", _database_url())
    monkeypatch.setenv("VTN_COOKIE_SECRET", "test-cookie-secret")
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    repo = JobRepository(_database_url())
    blob_store = LocalBlobStore(tmp_path / "blob")
    job_id = _prepare_review_ready_job(repo, blob_store)
    client = TestClient(_app(blob_store))

    stored = client.get(f"/jobs/{job_id}/note", headers=_headers()).json()
    summary_only = client.post(f"/jobs/{job_id}/export", headers=_headers())
    assert summary_only.status_code == 200
    summary_zip = _download_zip(blob_store, summary_only.json())
    assert_export_structure(summary_zip)
    assert _note_from_zip(summary_zip) == stored["markdown"]
    metadata = _metadata_from_zip(summary_zip)
    assert metadata["source_url"] == "https://www.youtube.com/watch?v=demo"
    assert metadata["depth"] == "balanced"
    assert metadata["transcript_source"] == "azure_speech"
    assert metadata["clips"][0]["scene_at_sec"] == "1.000"

    transcript_on = client.patch(
        f"/jobs/{job_id}/note",
        headers=_headers({"if-match": stored["etag"]}),
        json={"include_transcript": True},
    ).json()
    transcript_only = client.patch(
        f"/jobs/{job_id}/note",
        headers=_headers({"if-match": transcript_on["etag"]}),
        json={"include_summary": False},
    ).json()
    transcript_export = client.post(f"/jobs/{job_id}/export", headers=_headers())
    transcript_note = _note_from_zip(_download_zip(blob_store, transcript_export.json()))
    assert "Caption text" in transcript_note
    assert "> Transcript for intro." in transcript_note
    assert "Original prose" not in transcript_note
    assert (
        client.get(f"/jobs/{job_id}/note", headers=_headers()).json()["markdown"]
        == stored["markdown"]
    )

    client.patch(
        f"/jobs/{job_id}/note",
        headers=_headers({"if-match": transcript_only["etag"]}),
        json={"include_summary": True},
    ).json()
    with psycopg.connect(_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE clips SET needs_regen = true WHERE job_id = %s", (job_id,))
    both_export = client.post(f"/jobs/{job_id}/export", headers=_headers())
    both_note = _note_from_zip(_download_zip(blob_store, both_export.json()))
    assert "Needs regeneration" in both_note
    assert "Original prose" in both_note
    assert "> Transcript for intro." in both_note
    stored_after_marker = client.get(f"/jobs/{job_id}/note", headers=_headers()).json()["markdown"]
    assert_note_no_regen_marker(stored_after_marker)

    patched = client.patch(
        f"/clips/{repo.clips_view(job_id)['clips'][0]['id']}",
        headers=_headers({"if-match": repo.clips_view(job_id)["clips"][0]["etag"]}),
        json={"summary": "Edited after export"},
    )
    assert patched.status_code == 200
    assert client.get(f"/jobs/{job_id}", headers=_headers()).json()["status"] == "exported"
    second_export = client.post(f"/jobs/{job_id}/export", headers=_headers())
    second_note = _note_from_zip(_download_zip(blob_store, second_export.json()))
    assert "Edited after export" in second_note

    with psycopg.connect(_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM exports WHERE job_id = %s", (job_id,))
            assert cursor.fetchone()[0] >= 3
