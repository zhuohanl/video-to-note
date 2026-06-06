from __future__ import annotations

import os
import subprocess
from collections.abc import Iterator
from uuid import UUID

import bcrypt
import pytest
from fastapi.testclient import TestClient
from vtn_api.main import app
from vtn_core.invariants import (
    assert_clips_contiguous_ordered,
    assert_note_content_flags,
    assert_note_no_regen_marker,
    assert_note_no_transcript,
)
from vtn_storage.queue import InMemoryQueue
from vtn_storage.repos import JobRepository
from vtn_worker.main import process_next


def _database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", "postgresql://vtn:vtn@127.0.0.1:55432/vtn")


def _alembic(*args: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = _database_url()
    subprocess.run(["alembic", *args], check=True, env=env, capture_output=True, text=True)


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()


def _read_sse_frames(lines: Iterator[str], count: int) -> list[dict[str, object]]:
    frames: list[dict[str, object]] = []
    current: dict[str, object] = {}
    for line in lines:
        if not line:
            if current:
                frames.append(current)
                current = {}
                if len(frames) == count:
                    return frames
            continue
        field, value = line.split(": ", 1)
        if field == "id":
            current["id"] = int(value)
        elif field == "event":
            current["event"] = value
        elif field == "data":
            current["data"] = value
    return frames


@pytest.mark.asyncio
async def test_submit_to_review_ready_with_fake_worker(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", _database_url())
    monkeypatch.setenv("VTN_USERNAME", "local")
    monkeypatch.setenv("VTN_PASSWORD_HASH", _hash("secret"))
    monkeypatch.setenv("VTN_COOKIE_SECRET", "test-cookie-secret")
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    queue = InMemoryQueue()
    app.state.queue = queue
    client = TestClient(app, base_url="https://testserver")

    login = client.post("/login", json={"username": "local", "password": "secret"})
    assert login.status_code == 200

    submitted = client.post(
        "/jobs",
        json={"url": "https://www.youtube.com/watch?v=demo", "depth": "balanced"},
    )
    assert submitted.status_code == 202
    job_id = UUID(submitted.json()["job_id"])

    assert await process_next(queue, repo=JobRepository(_database_url()))

    with client.stream("GET", f"/jobs/{job_id}/events?replay_only=true") as response:
        assert response.status_code == 200
        sse_frames = _read_sse_frames(response.iter_lines(), 13)

    job = client.get(f"/jobs/{job_id}").json()
    clips = client.get(f"/jobs/{job_id}/clips").json()["clips"]
    note = client.get(f"/jobs/{job_id}/note").json()

    assert job["status"] == "review_ready"
    assert_clips_contiguous_ordered(clips)
    assert_note_no_transcript(note["markdown"])
    assert_note_no_regen_marker(note["markdown"])
    assert_note_content_flags(note)

    events = JobRepository(_database_url()).list_events_after(job_id, 0)
    assert [frame["event"] for frame in sse_frames] == [event["type"] for event in events]
    stage_sequence = [
        event["payload"]["stage"] for event in events if event["type"] == "stage"
    ]
    assert stage_sequence == [
        "resolving",
        "acquiring_media",
        "analyzing",
        "transcribe",
        "index visual",
        "extract style",
        "segmenting",
        "drafting",
    ]
    clip_ready_indexes = [
        event["payload"]["order_index"] for event in events if event["type"] == "clip.ready"
    ]
    assert clip_ready_indexes == [
        0,
        1,
    ]
    assert any(
        event["type"] == "warning" and event["payload"]["code"] == "asr_fallback"
        for event in events
    )
    assert events[-1]["type"] == "done"
