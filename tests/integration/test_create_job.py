from __future__ import annotations

import os
import subprocess
from uuid import UUID

import psycopg
from fastapi import FastAPI
from fastapi.testclient import TestClient
from vtn_api.auth import sign_session
from vtn_api.errors import ApiError, api_error_handler
from vtn_api.routes.jobs import router as jobs_router
from vtn_storage.queue import InMemoryQueue


def _database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", "postgresql://vtn:vtn@127.0.0.1:55432/vtn")


def _alembic(*args: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = _database_url()
    subprocess.run(["alembic", *args], check=True, env=env, capture_output=True, text=True)


def _app(queue: InMemoryQueue) -> FastAPI:
    app = FastAPI()
    app.state.queue = queue
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(jobs_router)
    return app


def _auth_headers() -> dict[str, str]:
    return {"cookie": f"vtn_session={sign_session('local')}"}


def test_create_job_persists_placeholder_prompt_cost_and_enqueues(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", _database_url())
    monkeypatch.setenv("VTN_COOKIE_SECRET", "test-cookie-secret")
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    queue = InMemoryQueue()

    response = TestClient(_app(queue)).post(
        "/jobs",
        headers=_auth_headers(),
        json={
            "url": "https://www.youtube.com/watch?v=demo",
            "depth": "balanced",
            "examples": [{"name": "sample.md", "markdown": "# Sample"}],
            "use_saved_style": True,
        },
    )

    assert response.status_code == 202
    body = response.json()
    job_id = UUID(body["job_id"])
    assert body["cost_estimate"] == {"usd": "0.0500", "breakdown": {"profile": "fake_stub"}}

    message = queue.receive()
    assert message is not None
    assert message.body == {"job_id": str(job_id), "attempt": 0}
    queue.complete(message)
    assert queue.receive() is None

    with psycopg.connect(_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT v.source_url, v.canonical_url, j.stage, j.status, p.depth,
                       p.examples, p.save_style_as_default, c.estimate_json
                FROM jobs j
                JOIN videos v ON v.id = j.video_id
                JOIN prompts p ON p.job_id = j.id
                JOIN job_costs c ON c.job_id = j.id
                WHERE j.id = %s
                """,
                (job_id,),
            )
            row = cursor.fetchone()

    assert row == (
        "https://www.youtube.com/watch?v=demo",
        None,
        "queued",
        "active",
        "balanced",
        [{"name": "sample.md", "markdown": "# Sample"}],
        False,
        {"usd": "0.0500", "breakdown": {"profile": "fake_stub"}},
    )

    get_response = TestClient(_app(queue)).get(f"/jobs/{job_id}", headers=_auth_headers())
    assert get_response.status_code == 200
    assert get_response.json() == {
        "id": str(job_id),
        "status": "active",
        "stage": "queued",
        "flags": {"is_polished": False, "clips_dirty": False},
        "error_code": None,
        "error_message": None,
        "cost": {
            "estimate_usd": "0.0500",
            "estimate": {"usd": "0.0500", "breakdown": {"profile": "fake_stub"}},
        },
    }


def test_custom_depth_requires_custom_prompt(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", _database_url())
    monkeypatch.setenv("VTN_COOKIE_SECRET", "test-cookie-secret")
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")

    response = TestClient(_app(InMemoryQueue())).post(
        "/jobs",
        headers=_auth_headers(),
        json={"url": "https://www.youtube.com/watch?v=demo", "depth": "custom"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "validation_error",
            "message": "custom_prompt is required when depth is custom",
        }
    }
