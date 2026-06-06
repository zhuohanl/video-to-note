from __future__ import annotations

import json
import os
import subprocess
import zipfile
from io import BytesIO
from pathlib import Path
from uuid import UUID

import bcrypt
import psycopg
import pytest
from fastapi.testclient import TestClient
from vtn_api.main import app
from vtn_core.invariants import (
    assert_baseline_immutable,
    assert_clips_contiguous_ordered,
    assert_export_structure,
    assert_note_content_flags,
    assert_note_no_regen_marker,
    assert_note_no_transcript,
    assert_reconciliation_flags,
)
from vtn_core.models import PromptDepth
from vtn_storage.blob import LocalBlobStore
from vtn_storage.queue import InMemoryQueue
from vtn_storage.repos import JobRepository
from vtn_worker.main import process_next

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


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()


def _both_etags(note_etag: str, clips_etag: str) -> str:
    return f"{note_etag}, {clips_etag}"


def _download_zip(blob_store: LocalBlobStore, response_body: dict[str, str]) -> bytes:
    prefix = "local://"
    assert response_body["download_url"].startswith(prefix)
    return blob_store.get(response_body["download_url"][len(prefix) :])


def _zip_note(zip_bytes: bytes) -> str:
    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        return archive.read("note.md").decode("utf-8")


def _zip_metadata(zip_bytes: bytes) -> dict[str, object]:
    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        return json.loads(archive.read("metadata.json").decode("utf-8"))


def _seed_scene_blobs(repo: JobRepository, blob_store: LocalBlobStore, job_id: UUID) -> None:
    for clip in repo.drafted_clip_rows(job_id):
        if clip["scene_blob_path"]:
            blob_store.put(str(clip["scene_blob_path"]), PNG_BYTES)


def _versions(job_id: UUID) -> list[dict[str, object]]:
    with psycopg.connect(_database_url(), row_factory=psycopg.rows.dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT seq, kind, is_baseline, note_markdown, note_settings, clips_snapshot
                FROM note_versions
                WHERE job_id = %s
                ORDER BY seq
                """,
                (job_id,),
            )
            return list(cursor.fetchall())


def _assert_stored_note_invariants(note: dict[str, object]) -> None:
    assert_note_content_flags(note)
    assert_note_no_regen_marker(str(note["markdown"]))
    assert_note_no_transcript(str(note["markdown"]))


@pytest.mark.asyncio
async def test_full_mocked_edit_review_export_round_trip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", _database_url())
    monkeypatch.setenv("VTN_USERNAME", "local")
    monkeypatch.setenv("VTN_PASSWORD_HASH", _hash("secret"))
    monkeypatch.setenv("VTN_COOKIE_SECRET", "test-cookie-secret")
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")

    queue = InMemoryQueue()
    blob_store = LocalBlobStore(tmp_path / "blob")
    app.state.queue = queue
    app.state.blob_store = blob_store
    client = TestClient(app, base_url="https://testserver")
    repo = JobRepository(_database_url())

    active_job_id = repo.create_submission(
        url="https://www.youtube.com/watch?v=active",
        depth=PromptDepth.balanced,
        custom_prompt=None,
        examples=[],
        use_saved_style=False,
    ).job_id
    repo.replace_clips(
        active_job_id,
        [
            {
                "start_sec": "0.000",
                "end_sec": "4.000",
                "title": "Active clip",
                "summary_seed": "Seed",
                "summary": "Draft",
                "classification": "mixed",
                "confidence": 0.9,
            }
        ],
    )
    active_clip = repo.clips_view(active_job_id)["clips"][0]

    login = client.post("/login", json={"username": "local", "password": "secret"})
    assert login.status_code == 200
    active_patch = client.patch(
        f"/clips/{active_clip['id']}",
        headers={"if-match": active_clip["etag"]},
        json={"summary": "blocked"},
    )
    assert active_patch.status_code == 409
    assert active_patch.json()["error"]["code"] == "job_not_review_ready"

    submitted = client.post(
        "/jobs",
        json={"url": "https://www.youtube.com/watch?v=demo", "depth": "balanced"},
    )
    assert submitted.status_code == 202
    job_id = UUID(submitted.json()["job_id"])
    assert await process_next(queue, repo=repo)
    _seed_scene_blobs(repo, blob_store, job_id)

    job = client.get(f"/jobs/{job_id}").json()
    assert job["status"] == "review_ready"
    clips_view = client.get(f"/jobs/{job_id}/clips").json()
    assert_clips_contiguous_ordered(clips_view["clips"])
    note = client.get(f"/jobs/{job_id}/note").json()
    _assert_stored_note_invariants(note)
    assert_reconciliation_flags(note, "auto_sync")

    stale_clip = client.patch(
        f"/clips/{clips_view['clips'][0]['id']}",
        headers={"if-match": '"stale"'},
        json={"title": "Stale title"},
    )
    assert stale_clip.status_code == 412
    assert stale_clip.json()["error"]["code"] == "stale_write"

    patched = client.patch(
        f"/clips/{clips_view['clips'][0]['id']}",
        headers={"if-match": clips_view["clips"][0]["etag"]},
        json={"summary": "Auto-synced summary"},
    )
    assert patched.status_code == 200
    after_patch_note = client.get(f"/jobs/{job_id}/note").json()
    assert "Auto-synced summary" in after_patch_note["markdown"]
    _assert_stored_note_invariants(after_patch_note)
    assert_reconciliation_flags(after_patch_note, "auto_sync")

    polished = client.put(
        f"/jobs/{job_id}/note",
        headers={"if-match": after_patch_note["etag"]},
        json={"markdown": "# Polished review note\n\nHuman-written prose."},
    )
    assert polished.status_code == 200
    polished_note = polished.json()
    assert_reconciliation_flags(polished_note, "keep")
    _assert_stored_note_invariants(polished_note)

    pre_split_clips = client.get(f"/jobs/{job_id}/clips").json()
    split_needs_ack = client.post(
        f"/clips/{pre_split_clips['clips'][0]['id']}/split",
        headers={"if-match": pre_split_clips["collection_etag"]},
        json={"at_sec": "4.000"},
    )
    assert split_needs_ack.status_code == 409
    assert split_needs_ack.json()["error"]["code"] == "needs_ack"

    split = client.post(
        f"/clips/{pre_split_clips['clips'][0]['id']}/split?ack=1",
        headers={"if-match": pre_split_clips["collection_etag"]},
        json={"at_sec": "4.000"},
    )
    assert split.status_code == 200
    split_clips = split.json()["clips"]
    assert_clips_contiguous_ordered(split_clips)
    assert split_clips[0]["needs_regen"] is True
    assert split_clips[1]["needs_regen"] is True
    assert split_clips[1]["title"].endswith("(cont.)")
    _seed_scene_blobs(repo, blob_store, job_id)
    dirty_note = client.get(f"/jobs/{job_id}/note").json()
    assert dirty_note["markdown"] == polished_note["markdown"]
    assert_reconciliation_flags(dirty_note, "clip_change_polished")
    _assert_stored_note_invariants(dirty_note)

    stale_regenerate = client.post(
        f"/clips/{split_clips[0]['id']}/regenerate",
        headers={"if-match": pre_split_clips["clips"][0]["etag"]},
    )
    assert stale_regenerate.status_code == 412
    assert stale_regenerate.json()["error"]["code"] == "stale_write"

    regenerated = client.post(
        f"/clips/{split_clips[0]['id']}/regenerate?ack=1",
        headers={"if-match": split_clips[0]["etag"]},
    )
    assert regenerated.status_code == 200
    assert regenerated.json()["needs_regen"] is False
    dirty_after_regen = client.get(f"/jobs/{job_id}/note").json()
    assert_reconciliation_flags(dirty_after_regen, "clip_change_polished")
    _assert_stored_note_invariants(dirty_after_regen)

    stale_rebuild = client.post(
        f"/jobs/{job_id}/note/rebuild",
        headers={"if-match": polished_note["etag"]},
    )
    assert stale_rebuild.status_code == 412
    assert stale_rebuild.json()["error"]["code"] == "stale_write"

    rebuilt = client.post(
        f"/jobs/{job_id}/note/rebuild",
        headers={"if-match": dirty_after_regen["etag"]},
    )
    assert rebuilt.status_code == 200
    rebuilt_note = rebuilt.json()
    assert "Human-written prose" not in rebuilt_note["markdown"]
    assert "Auto-synced summary" in rebuilt_note["markdown"]
    assert_reconciliation_flags(rebuilt_note, "rebuild")
    _assert_stored_note_invariants(rebuilt_note)

    current_clips = client.get(f"/jobs/{job_id}/clips").json()
    stale_manual = client.post(
        f"/jobs/{job_id}/versions",
        headers={"if-match": _both_etags('"stale"', current_clips["collection_etag"])},
        json={"label": "bad"},
    )
    assert stale_manual.status_code == 412

    manual = client.post(
        f"/jobs/{job_id}/versions",
        headers={"if-match": _both_etags(rebuilt_note["etag"], current_clips["collection_etag"])},
        json={"label": "rebuilt checkpoint"},
    )
    assert manual.status_code == 200
    manual_seq = manual.json()["seq"]
    changed = client.put(
        f"/jobs/{job_id}/note",
        headers={"if-match": rebuilt_note["etag"]},
        json={"markdown": "# Temporary edit"},
    )
    assert changed.status_code == 200
    before_restore_note = changed.json()
    before_restore_clips = client.get(f"/jobs/{job_id}/clips").json()
    stale_restore = client.post(
        f"/jobs/{job_id}/versions/{manual_seq}/restore",
        headers={"if-match": _both_etags(before_restore_note["etag"], '"stale"')},
    )
    assert stale_restore.status_code == 412
    restored = client.post(
        f"/jobs/{job_id}/versions/{manual_seq}/restore",
        headers={
            "if-match": _both_etags(
                before_restore_note["etag"], before_restore_clips["collection_etag"]
            )
        },
    )
    assert restored.status_code == 200
    restored_note = client.get(f"/jobs/{job_id}/note").json()
    restored_clips = client.get(f"/jobs/{job_id}/clips").json()
    assert restored_note["markdown"] == rebuilt_note["markdown"]
    assert restored_note["include_summary"] is True
    assert restored_note["include_transcript"] is False
    assert_reconciliation_flags(restored_note, "restore")
    _assert_stored_note_invariants(restored_note)

    both_false = client.patch(
        f"/jobs/{job_id}/note",
        headers={"if-match": restored_note["etag"]},
        json={"include_summary": False, "include_transcript": False},
    )
    assert both_false.status_code == 422
    assert both_false.json()["error"]["code"] == "validation_error"

    summary_export = client.post(f"/jobs/{job_id}/export")
    assert summary_export.status_code == 200
    summary_zip = _download_zip(blob_store, summary_export.json())
    assert_export_structure(summary_zip)
    summary_note = _zip_note(summary_zip)
    assert "Auto-synced summary" in summary_note
    assert "Needs regeneration" in summary_note
    assert client.get(f"/jobs/{job_id}/note").json()["markdown"] == restored_note["markdown"]
    assert ">" not in summary_note

    summary_stored = client.get(f"/jobs/{job_id}/note").json()
    transcript_on = client.patch(
        f"/jobs/{job_id}/note",
        headers={"if-match": summary_stored["etag"]},
        json={"include_transcript": True},
    ).json()
    transcript_only = client.patch(
        f"/jobs/{job_id}/note",
        headers={"if-match": transcript_on["etag"]},
        json={"include_summary": False},
    ).json()
    transcript_export = client.post(f"/jobs/{job_id}/export")
    assert transcript_export.status_code == 200
    transcript_zip = _download_zip(blob_store, transcript_export.json())
    assert_export_structure(transcript_zip)
    transcript_note = _zip_note(transcript_zip)
    assert "> Worker events." in transcript_note
    assert "Auto-synced summary" not in transcript_note
    assert client.get(f"/jobs/{job_id}/note").json()["markdown"] == restored_note["markdown"]

    both_mode = client.patch(
        f"/jobs/{job_id}/note",
        headers={"if-match": transcript_only["etag"]},
        json={"include_summary": True},
    ).json()
    both_export = client.post(f"/jobs/{job_id}/export")
    assert both_export.status_code == 200
    both_zip = _download_zip(blob_store, both_export.json())
    assert_export_structure(both_zip)
    both_note = _zip_note(both_zip)
    assert "Auto-synced summary" in both_note
    assert "> Worker events." in both_note
    assert len({summary_note, transcript_note, both_note}) == 3
    metadata = _zip_metadata(both_zip)
    assert metadata["source_url"] == "https://www.youtube.com/watch?v=demo"
    assert len(metadata["clips"]) == len(restored_clips["clips"])

    exported_job = client.get(f"/jobs/{job_id}").json()
    assert exported_job["status"] == "exported"
    exported_clip = client.patch(
        f"/clips/{restored_clips['clips'][0]['id']}",
        headers={"if-match": restored_clips["clips"][0]["etag"]},
        json={"scene_caption": "Edited after export"},
    )
    assert exported_clip.status_code == 200
    assert client.get(f"/jobs/{job_id}").json()["status"] == "exported"
    exported_note = client.get(f"/jobs/{job_id}/note").json()
    assert exported_note["include_summary"] == both_mode["include_summary"]
    assert exported_note["include_transcript"] == both_mode["include_transcript"]
    _assert_stored_note_invariants(exported_note)

    version_rows = _versions(job_id)
    assert_baseline_immutable(version_rows)
    assert {"initial", "auto_edit", "auto_pre_change", "auto_rebuild", "manual", "restore"} <= {
        str(row["kind"]) for row in version_rows
    }
