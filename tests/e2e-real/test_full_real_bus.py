from __future__ import annotations

import os
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from vtn_api.main import app
from vtn_storage.servicebus import ServiceBusQueue

pytestmark = pytest.mark.real_infra


def _require_env(*names: str) -> None:
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        pytest.skip(f"missing env vars: {', '.join(missing)}")


def test_full_real_bus_submit_worker_sse() -> None:
    if os.environ.get("RUN_REAL") != "1":
        pytest.skip("set RUN_REAL=1 to run full real Service Bus e2e")

    _require_env(
        "DATABASE_URL",
        "VTN_PASSWORD",
        "VTN_PASSWORD_HASH",
        "VTN_COOKIE_SECRET",
    )
    if not (
        os.environ.get("AZURE_SERVICE_BUS_CONNECTION_STRING")
        or os.environ.get("AZURE_SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE")
    ):
        pytest.skip("missing Service Bus connection string or namespace")

    app.state.queue = ServiceBusQueue.from_env()
    client = TestClient(app)
    login = client.post(
        "/login",
        json={
            "username": os.environ.get("VTN_USERNAME", "local"),
            "password": os.environ["VTN_PASSWORD"],
        },
    )
    assert login.status_code == 200

    created = client.post(
        "/jobs",
        json={
            "url": os.environ.get(
                "VTN_REAL_VIDEO_URL",
                "https://www.youtube.com/watch?v=jNQXAC9IVRw",
            ),
            "depth": "balanced",
            "custom_prompt": None,
            "examples": [],
            "use_saved_style": False,
        },
    )
    assert created.status_code == 202
    job_id = created.json()["job_id"]

    env = {
        **os.environ,
        "APP_PROFILE": "azure",
    }
    completed = subprocess.run(
        [sys.executable, "-m", "vtn_worker.main"],
        env=env,
        check=False,
        text=True,
        capture_output=True,
        timeout=int(os.environ.get("VTN_REAL_TIMEOUT_SECONDS", "900")),
    )
    assert completed.returncode == 0, completed.stderr

    job = client.get(f"/jobs/{job_id}")
    assert job.status_code == 200
    assert job.json()["status"] == "review_ready"

    clips = client.get(f"/jobs/{job_id}/clips")
    note = client.get(f"/jobs/{job_id}/note")
    assert clips.status_code == 200
    assert note.status_code == 200
    assert clips.json()["clips"]
    assert note.json()["markdown"].strip()

    events = client.get(f"/jobs/{job_id}/events?replay_only=true")
    assert events.status_code == 200
    body = events.text
    assert "event: stage" in body
    assert "event: done" in body
