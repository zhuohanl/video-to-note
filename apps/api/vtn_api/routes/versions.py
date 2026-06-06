from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from vtn_storage.repos import JobRepository

from vtn_api.auth import require_session
from vtn_api.deps import job_repository
from vtn_api.errors import ApiError
from vtn_api.schemas import CreateVersion, VersionView

router = APIRouter()
SessionDep = Annotated[str, Depends(require_session)]
RepoDep = Annotated[JobRepository, Depends(job_repository)]


@router.get("/jobs/{job_id}/versions")
def list_versions(
    job_id: UUID,
    session: SessionDep,
    repo: RepoDep,
) -> dict[str, list[VersionView]]:
    del session
    return {"versions": [VersionView.model_validate(row) for row in repo.list_versions(job_id)]}


@router.post("/jobs/{job_id}/versions", response_model=VersionView)
def create_version(
    job_id: UUID,
    body: CreateVersion,
    session: SessionDep,
    repo: RepoDep,
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> VersionView:
    del session
    note_etag, clips_etag = _both_etags(if_match)
    result = repo.create_manual_version(
        job_id,
        expected_note_etag=note_etag,
        expected_clips_etag=clips_etag,
        label=body.label,
    )
    return _version_response(result)


@router.post("/jobs/{job_id}/versions/{seq}/restore")
def restore_version(
    job_id: UUID,
    seq: int,
    session: SessionDep,
    repo: RepoDep,
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, str]:
    del session
    note_etag, clips_etag = _both_etags(if_match)
    result = repo.restore_version(
        job_id,
        seq,
        expected_note_etag=note_etag,
        expected_clips_etag=clips_etag,
    )
    match result["status"]:
        case "ok":
            return {"status": "restored"}
        case "stale_write":
            raise ApiError("stale_write", "Project ETag is stale", 412)
        case "version_not_found":
            raise ApiError("version_not_found", "Version not found", 404)
        case _:
            raise RuntimeError(f"unknown restore result: {result['status']}")


def _version_response(result: dict[str, object]) -> VersionView:
    match result["status"]:
        case "ok":
            return VersionView.model_validate(result["version"])
        case "stale_write":
            raise ApiError("stale_write", "Project ETag is stale", 412)
        case _:
            raise RuntimeError(f"unknown version result: {result['status']}")


def _both_etags(value: str | None) -> tuple[str, str]:
    if value is None:
        raise ApiError("stale_write", "If-Match is required", 412)
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 2 or not all(parts):
        raise ApiError("stale_write", "Both note and clips ETags are required", 412)
    return parts[0], parts[1]
