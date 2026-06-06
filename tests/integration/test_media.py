from __future__ import annotations

import os
import subprocess
from pathlib import Path
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from vtn_api.auth import sign_session
from vtn_api.errors import ApiError, api_error_handler
from vtn_api.routes.media import router as media_router
from vtn_core.models import JobStatus, PromptDepth
from vtn_storage.blob import LocalBlobStore
from vtn_storage.repos import JobRepository
from vtn_visual.sampler import generate_test_video


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
    app.include_router(media_router)
    return app


def _prepare_media_job(repo: JobRepository, blob_store: LocalBlobStore, video_path: Path) -> UUID:
    job_id = repo.create_submission(
        url="https://www.youtube.com/watch?v=demo",
        depth=PromptDepth.balanced,
        custom_prompt=None,
        examples=[],
        use_saved_style=False,
    ).job_id
    video_id = repo.get_job_video_id(job_id)
    blob_store.put(f"proxy/{video_id}.mp4", video_path.read_bytes())
    repo.set_proxy_ready(video_id, f"proxy/{video_id}.mp4")
    repo.replace_visual_events(
        video_id,
        [
            {
                "at_sec": "0.000",
                "event_type": "keyframe",
                "confidence": 0.9,
                "ocr_text": "Intro",
                "phash": "8f1c2a3b4d5e6071",
                "frame_blob_path": "frames/intro.png",
            }
        ],
    )
    repo.replace_clips(
        job_id,
        [
            {
                "start_sec": "0.000",
                "end_sec": "2.000",
                "title": "Intro",
                "summary_seed": "Intro",
                "summary": "Summary",
                "classification": "mixed",
                "confidence": 0.9,
            }
        ],
    )
    repo.mark_review_ready(job_id)
    assert repo.get_job(job_id).status == JobStatus.review_ready
    return job_id


@pytest.mark.asyncio
async def test_media_range_candidates_and_set_scene_are_etag_guarded(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", _database_url())
    monkeypatch.setenv("VTN_COOKIE_SECRET", "test-cookie-secret")
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    video = tmp_path / "synthetic.mp4"
    generate_test_video(video, duration_sec=2)
    repo = JobRepository(_database_url())
    blob_store = LocalBlobStore(tmp_path / "blob")
    job_id = _prepare_media_job(repo, blob_store, video)
    video_id = repo.get_job_video_id(job_id)
    clip = repo.clips_view(job_id)["clips"][0]
    client = TestClient(_app(blob_store))

    partial = client.get(
        f"/videos/{video_id}/stream",
        headers=_headers({"range": "bytes=0-9"}),
    )
    assert partial.status_code == 206
    assert partial.content == video.read_bytes()[:10]
    assert partial.headers["content-range"].startswith("bytes 0-9/")

    candidates = client.get(f"/clips/{clip['id']}/scene-candidates", headers=_headers())
    assert candidates.status_code == 200
    assert candidates.json()["candidates"][0]["frame_blob_path"] == "frames/intro.png"

    stale = client.post(
        f"/clips/{clip['id']}/scene",
        headers=_headers({"if-match": '"stale"'}),
        json={"at_sec": "1.000"},
    )
    assert stale.status_code == 412

    updated = client.post(
        f"/clips/{clip['id']}/scene",
        headers=_headers({"if-match": clip["etag"]}),
        json={"at_sec": "1.000"},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["scene_source"] == "manual"
    assert body["etag"] != clip["etag"]
    assert blob_store.get(body["scene_blob_path"]).startswith(b"\x89PNG")
