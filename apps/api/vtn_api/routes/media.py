from __future__ import annotations

import subprocess
from decimal import Decimal
from tempfile import TemporaryDirectory
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import Response
from pydantic import BaseModel
from vtn_core.models import JobStatus
from vtn_storage.blob import BlobStore
from vtn_storage.repos import JobRepository
from vtn_visual.sampler import ffmpeg_exe

from vtn_api.auth import require_session
from vtn_api.deps import blob_store, job_repository
from vtn_api.errors import ApiError

router = APIRouter()
SessionDep = Annotated[str, Depends(require_session)]
RepoDep = Annotated[JobRepository, Depends(job_repository)]
BlobDep = Annotated[BlobStore, Depends(blob_store)]


class SetSceneRequest(BaseModel):
    at_sec: Decimal


@router.get("/videos/{video_id}/stream")
def stream_video(
    video_id: UUID,
    session: SessionDep,
    repo: RepoDep,
    blobs: BlobDep,
    range_header: str | None = Header(default=None, alias="Range"),
) -> Response:
    del session
    data = blobs.get(repo.video_proxy_key(video_id))
    start, end = _range(range_header, len(data))
    if range_header:
        body = data[start : end + 1]
        return Response(
            body,
            status_code=206,
            media_type="video/mp4",
            headers={
                "Content-Range": f"bytes {start}-{end}/{len(data)}",
                "Accept-Ranges": "bytes",
            },
        )
    return Response(data, media_type="video/mp4", headers={"Accept-Ranges": "bytes"})


@router.get("/clips/{clip_id}/scene-candidates")
def scene_candidates(
    clip_id: UUID,
    session: SessionDep,
    repo: RepoDep,
) -> dict[str, object]:
    del session
    _require_review_ready(repo, clip_id)
    return {"candidates": repo.scene_candidates(clip_id)}


@router.post("/clips/{clip_id}/scene")
def set_scene(
    clip_id: UUID,
    body: SetSceneRequest,
    session: SessionDep,
    repo: RepoDep,
    blobs: BlobDep,
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, object]:
    del session
    if if_match is None:
        raise ApiError("stale_write", "If-Match is required", 412)
    context = _require_review_ready(repo, clip_id)
    proxy = blobs.get(repo.video_proxy_key(cast(UUID, context["video_id"])))
    scene_blob_path = f"frames/manual/{clip_id}-{int(body.at_sec * 1000)}.png"
    with TemporaryDirectory() as temp_dir:
        input_path = f"{temp_dir}/proxy.mp4"
        output_path = f"{temp_dir}/scene.png"
        with open(input_path, "wb") as file:
            file.write(proxy)
        subprocess.run(
            [
                ffmpeg_exe(),
                "-y",
                "-ss",
                str(body.at_sec),
                "-i",
                input_path,
                "-frames:v",
                "1",
                output_path,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        with open(output_path, "rb") as file:
            blobs.put(scene_blob_path, file.read())
    updated = repo.set_manual_scene(
        clip_id,
        expected_etag=if_match,
        at_sec=body.at_sec,
        scene_blob_path=scene_blob_path,
    )
    if updated["stale"]:
        raise ApiError("stale_write", "Clip ETag is stale", 412)
    return updated


def _range(range_header: str | None, size: int) -> tuple[int, int]:
    if not range_header:
        return 0, size - 1
    unit, _, value = range_header.partition("=")
    if unit.lower() != "bytes":
        raise ApiError("validation_error", "Only byte ranges are supported", 422)
    start_raw, _, end_raw = value.partition("-")
    start = int(start_raw or 0)
    end = int(end_raw or size - 1)
    if start < 0 or end < start or end >= size:
        raise ApiError("validation_error", "Invalid byte range", 422)
    return start, end


def _require_review_ready(repo: JobRepository, clip_id: UUID) -> dict[str, object]:
    context = repo.clip_media_context(clip_id)
    if context["status"] not in {JobStatus.review_ready.value, JobStatus.exported.value}:
        raise ApiError("job_not_review_ready", "Job is not review-ready", 409)
    return context
