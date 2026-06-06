from __future__ import annotations

import json
import os
import time
from collections.abc import Iterator
from typing import Any

import httpx
import pytest

pytestmark = pytest.mark.real_infra


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"missing {name}")
    return value


def _events(lines: Iterator[str]) -> Iterator[dict[str, Any]]:
    event_type = "message"
    data = ""
    for line in lines:
      if line.startswith("event:"):
          event_type = line.partition(":")[2].strip()
      elif line.startswith("data:"):
          data = line.partition(":")[2].strip()
      elif not line:
          if data:
              yield {"type": event_type, "payload": json.loads(data)}
          event_type = "message"
          data = ""


def test_deployed_api_journey() -> None:
    if os.environ.get("RUN_REAL") != "1":
        pytest.skip("set RUN_REAL=1 to run deployed real-infra journey")

    base_url = os.environ.get("DEPLOYED_API_URL") or os.environ.get("API_URL")
    if not base_url:
        pytest.skip("missing DEPLOYED_API_URL or API_URL")

    username = os.environ.get("VTN_USERNAME", "local")
    password = _required("VTN_PASSWORD")
    video_url = os.environ.get(
        "VTN_REAL_VIDEO_URL",
        "https://www.youtube.com/watch?v=jNQXAC9IVRw",
    )

    with httpx.Client(base_url=base_url, timeout=30.0, follow_redirects=True) as client:
        login = client.post("/login", json={"username": username, "password": password})
        assert login.status_code == 200

        created = client.post(
            "/jobs",
            json={
                "url": video_url,
                "depth": "balanced",
                "custom_prompt": None,
                "examples": [],
                "use_saved_style": False,
            },
        )
        assert created.status_code == 202
        job_id = created.json()["job_id"]

        seen_done = False
        deadline = time.monotonic() + int(os.environ.get("VTN_REAL_TIMEOUT_SECONDS", "900"))
        with client.stream("GET", f"/jobs/{job_id}/events") as stream:
            for event in _events(stream.iter_lines()):
                if event["type"] in {"done", "review_ready"}:
                    seen_done = True
                    break
                if event["type"] == "error":
                    pytest.fail(f"deployed worker error event: {event['payload']}")
                if time.monotonic() > deadline:
                    break
        assert seen_done

        clips_response = client.get(f"/jobs/{job_id}/clips")
        assert clips_response.status_code == 200
        clips = clips_response.json()
        assert clips["clips"]
        assert clips["collection_etag"]
        assert all(clip["start_sec"] <= clip["end_sec"] for clip in clips["clips"])

        note_response = client.get(f"/jobs/{job_id}/note")
        assert note_response.status_code == 200
        note = note_response.json()
        assert note["markdown"].strip()
        assert note["include_summary"] or note["include_transcript"]

        first_clip = clips["clips"][0]
        edited = client.patch(
            f"/clips/{first_clip['id']}",
            headers={"if-match": first_clip["etag"]},
            json={"summary": first_clip.get("summary") or "Reviewed summary"},
        )
        assert edited.status_code in {200, 409}

        exported = client.post(f"/jobs/{job_id}/export")
        assert exported.status_code == 200
        download_url = exported.json()["download_url"]
        assert download_url

        zip_response = client.get(download_url)
        assert zip_response.status_code == 200
        assert zip_response.content.startswith(b"PK")
