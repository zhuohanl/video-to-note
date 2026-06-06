from __future__ import annotations

import json
import os
import subprocess
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from vtn_api.auth import sign_session
from vtn_api.errors import ApiError, api_error_handler
from vtn_api.routes.jobs import router as jobs_router
from vtn_api.sse import _event_stream
from vtn_api.sse import router as sse_router
from vtn_core.models import PromptDepth
from vtn_storage.queue import InMemoryQueue
from vtn_storage.repos import JobRepository


def _database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", "postgresql://vtn:vtn@127.0.0.1:55432/vtn")


def _alembic(*args: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = _database_url()
    subprocess.run(["alembic", *args], check=True, env=env, capture_output=True, text=True)


def _app() -> FastAPI:
    app = FastAPI()
    app.state.queue = InMemoryQueue()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(jobs_router)
    app.include_router(sse_router)
    return app


def _headers(last_event_id: int | None = None) -> dict[str, str]:
    headers = {"cookie": f"vtn_session={sign_session('local')}"}
    if last_event_id is not None:
        headers["last-event-id"] = str(last_event_id)
    return headers


def _create_job() -> UUID:
    repo = JobRepository(_database_url())
    return repo.create_submission(
        url="https://www.youtube.com/watch?v=demo",
        depth=PromptDepth.balanced,
        custom_prompt=None,
        examples=[],
        use_saved_style=False,
    ).job_id


def _parse_sse_frame(frame: str) -> dict[str, object]:
    parsed: dict[str, object] = {}
    for line in frame.splitlines():
        if not line:
            continue
        field, value = line.split(": ", 1)
        if field == "id":
            parsed["id"] = int(value)
        elif field == "event":
            parsed["event"] = value
        elif field == "data":
            parsed["data"] = json.loads(value)
    return parsed


async def _collect_replay(job_id: UUID, last_event_id: int, count: int) -> list[dict[str, object]]:
    stream = _event_stream(JobRepository(_database_url()), job_id, last_event_id)
    frames: list[dict[str, object]] = []
    try:
        async for frame in stream:
            frames.append(_parse_sse_frame(frame))
            if len(frames) == count:
                break
    finally:
        await stream.aclose()
    return frames


@pytest.mark.asyncio
async def test_sse_replays_events_after_last_event_id_and_requires_cookie(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", _database_url())
    monkeypatch.setenv("VTN_COOKIE_SECRET", "test-cookie-secret")
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    job_id = _create_job()
    repo = JobRepository(_database_url())
    repo.emit_event(job_id, "stage", {"stage": "resolving"})
    repo.emit_event(job_id, "clip.ready", {"clip_id": "clip-1", "order_index": 0})
    repo.emit_event(job_id, "done", {})
    client = TestClient(_app())

    unauthorized = client.get(f"/jobs/{job_id}/events")
    assert unauthorized.status_code == 401
    assert unauthorized.json() == {"error": {"code": "unauthorized", "message": "Missing session"}}

    frames = await _collect_replay(job_id, last_event_id=0, count=3)
    assert frames == [
        {"id": 1, "event": "stage", "data": {"stage": "resolving"}},
        {"id": 2, "event": "clip.ready", "data": {"clip_id": "clip-1", "order_index": 0}},
        {"id": 3, "event": "done", "data": {}},
    ]

    replayed = await _collect_replay(job_id, last_event_id=2, count=1)
    assert replayed == [{"id": 3, "event": "done", "data": {}}]
