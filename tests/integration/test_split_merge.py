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
from vtn_core.invariants import assert_clips_contiguous_ordered, assert_reconciliation_flags
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
                "summary_seed": "Seed A",
                "summary": "Summary A",
                "classification": "mixed",
                "confidence": 0.91,
            },
            {
                "start_sec": "10.000",
                "end_sec": "20.000",
                "title": "Deep Dive",
                "summary_seed": "Seed B",
                "summary": "Summary B",
                "classification": "text_led",
                "confidence": 0.82,
            },
        ],
    )
    for index, clip in enumerate(repo.clip_rows(job_id)):
        repo.update_clip_draft(
            clip_id=clip["id"],
            summary=f"Summary {'A' if index == 0 else 'B'}",
            scene_at_sec="3.000" if index == 0 else "12.000",
            scene_blob_path=f"frames/{index}.png",
        )
    clips = repo.drafted_clip_rows(job_id)
    with psycopg.connect(_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE clips
                SET scene_caption = 'Opening caption',
                    scene_source = 'manual'
                WHERE job_id = %s AND order_index = 0
                """,
                (job_id,),
            )
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


def test_split_merge_collection_etag_placeholders_and_needs_ack(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", _database_url())
    monkeypatch.setenv("VTN_COOKIE_SECRET", "test-cookie-secret")
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    repo = JobRepository(_database_url())
    client = TestClient(_app())
    job_id = _prepare_review_ready_job(repo)

    view = repo.clips_view(job_id)
    stale = client.post(
        f"/clips/{view['clips'][0]['id']}/split",
        headers=_headers({"if-match": '"stale"'}),
        json={"at_sec": "4.000"},
    )
    assert stale.status_code == 412
    assert stale.json()["error"]["code"] == "stale_write"

    split = client.post(
        f"/clips/{view['clips'][0]['id']}/split",
        headers=_headers({"if-match": view["collection_etag"]}),
        json={"at_sec": "4.000"},
    )
    assert split.status_code == 200
    split_clips = split.json()["clips"]
    assert_clips_contiguous_ordered(split_clips)
    assert [clip["order_index"] for clip in split_clips] == [0, 1, 2]
    assert split_clips[0]["end_sec"] == "4.000"
    assert split_clips[1]["start_sec"] == "4.000"
    assert split_clips[1]["title"] == "Intro (cont.)"
    assert split_clips[0]["summary"] == "Summary A"
    assert split_clips[1]["summary"] == "Summary A"
    assert split_clips[0]["needs_regen"] is True
    assert split_clips[1]["needs_regen"] is True
    assert split_clips[0]["scene_at_sec"] == "3.000"
    assert split_clips[0]["scene_caption"] == "Opening caption"
    assert split_clips[0]["scene_source"] == "manual"
    assert split_clips[1]["scene_at_sec"] == "4.000"
    assert split_clips[1]["scene_caption"] is None
    assert split_clips[1]["scene_source"] == "auto"
    split_note = client.get(f"/jobs/{job_id}/note", headers=_headers()).json()
    assert "Intro (cont.)" in split_note["markdown"]
    assert_reconciliation_flags(split_note, "auto_sync")

    stale_after_split = client.post(
        f"/clips/{view['clips'][0]['id']}/split",
        headers=_headers({"if-match": view["collection_etag"]}),
        json={"at_sec": "2.000"},
    )
    assert stale_after_split.status_code == 412

    after_split = repo.clips_view(job_id)
    merge = client.post(
        "/clips/merge",
        headers=_headers({"if-match": after_split["collection_etag"]}),
        json={"clip_ids": [split_clips[0]["id"], split_clips[1]["id"]]},
    )
    assert merge.status_code == 200
    merged_clips = merge.json()["clips"]
    assert_clips_contiguous_ordered(merged_clips)
    assert len(merged_clips) == 2
    assert merged_clips[0]["title"] == "Intro"
    assert merged_clips[0]["summary"] == "Summary A\n\nSummary A"
    assert merged_clips[0]["scene_at_sec"] == "3.000"
    assert merged_clips[0]["scene_caption"] == "Opening caption"
    assert merged_clips[0]["scene_source"] == "manual"
    assert merged_clips[0]["needs_regen"] is True
    merged_note = client.get(f"/jobs/{job_id}/note", headers=_headers()).json()
    assert "Summary A\n\nSummary A" in merged_note["markdown"]
    assert_reconciliation_flags(merged_note, "auto_sync")

    _set_polished(job_id)
    polished = repo.clips_view(job_id)
    needs_ack = client.post(
        f"/clips/{polished['clips'][0]['id']}/split",
        headers=_headers({"if-match": polished["collection_etag"]}),
        json={"at_sec": "2.000"},
    )
    assert needs_ack.status_code == 409
    assert needs_ack.json()["error"]["code"] == "needs_ack"

    acked = client.post(
        f"/clips/{polished['clips'][0]['id']}/split?ack=1",
        headers=_headers({"if-match": polished["collection_etag"]}),
        json={"at_sec": "2.000"},
    )
    assert acked.status_code == 200
    note_after_ack = client.get(f"/jobs/{job_id}/note", headers=_headers()).json()
    assert_reconciliation_flags(note_after_ack, "clip_change_polished")
    assert _version_kinds(job_id) == ["initial", "auto_pre_change"]
