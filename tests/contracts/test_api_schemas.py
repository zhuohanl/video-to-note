from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from vtn_api.errors import ERROR_CODES, ApiError, api_error_handler
from vtn_api.schemas import (
    ClipsView,
    ClipView,
    CreateJob,
    CreateVersion,
    ExportView,
    JobView,
    LoginBody,
    MergeBody,
    NoteView,
    PatchClip,
    PatchNote,
    PutNote,
    SplitBody,
    VersionView,
)
from vtn_core.models import ClipStatus, JobStage, JobStatus, PromptDepth, SceneSource


def test_endpoint_schemas_accept_good_payloads() -> None:
    job_id = uuid4()
    clip_id = uuid4()

    assert LoginBody(username="local", password="secret").username == "local"
    assert CreateJob(url="https://www.youtube.com/watch?v=abc", depth=PromptDepth.balanced).depth
    assert JobView(
        id=job_id,
        status=JobStatus.active,
        stage=JobStage.queued,
        cost={"estimate_usd": "0.10"},
    ).id == job_id
    clip = ClipView(
        id=clip_id,
        order_index=0,
        start_sec=Decimal("0.000"),
        end_sec=Decimal("10.000"),
        status=ClipStatus.ready,
        scene_source=SceneSource.auto,
        etag='"clip-1"',
    )
    assert ClipsView(clips=[clip], collection_etag='"clips-1"').clips[0].id == clip_id
    assert NoteView(markdown="# Note", etag='"note-1"').include_summary is True
    assert PatchClip(title="New title", summary="New summary", scene_caption="Caption").title
    assert SplitBody(at_sec=Decimal("5.000")).at_sec == Decimal("5.000")
    assert MergeBody(clip_ids=[clip_id]).clip_ids == [clip_id]
    assert PutNote(markdown="# Edited").markdown == "# Edited"
    assert PatchNote(include_transcript=True).include_transcript is True
    assert VersionView(seq=1, label="v1", kind="initial", baseline=True).baseline is True
    assert CreateVersion(label="manual").label == "manual"
    assert ExportView(download_url="local://exports/job.zip").download_url


@pytest.mark.parametrize(
    ("schema", "payload"),
    [
        (LoginBody, {"username": "", "password": "secret"}),
        (CreateJob, {"url": "not-a-url", "depth": "balanced"}),
        (SplitBody, {"at_sec": -1}),
        (MergeBody, {"clip_ids": []}),
        (PatchNote, {"include_summary": False, "include_transcript": False}),
    ],
)
def test_endpoint_schemas_reject_bad_payloads(schema: type, payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        schema.model_validate(payload)


def test_error_codes_are_pinned() -> None:
    assert ERROR_CODES == {
        "unsupported_url",
        "video_unavailable",
        "transcript_failed",
        "job_not_review_ready",
        "needs_ack",
        "stale_write",
        "version_not_found",
        "unauthorized",
        "validation_error",
    }


def test_api_error_handler_renders_exact_envelope() -> None:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)

    @app.get("/boom")
    async def boom() -> None:
        raise ApiError("stale_write", "ETag mismatch", 412)

    response = TestClient(app).get("/boom")

    assert response.status_code == 412
    assert response.json() == {"error": {"code": "stale_write", "message": "ETag mismatch"}}
