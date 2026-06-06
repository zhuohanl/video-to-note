from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from vtn_notes.assemble import assemble_markdown
from vtn_storage.repos import JobRepository

from vtn_api.auth import require_session
from vtn_api.deps import job_repository
from vtn_api.errors import ApiError
from vtn_api.schemas import ClipsView, ClipView, PatchClip

router = APIRouter()
SessionDep = Annotated[str, Depends(require_session)]
RepoDep = Annotated[JobRepository, Depends(job_repository)]


@router.get("/jobs/{job_id}/clips", response_model=ClipsView)
def get_clips(job_id: UUID, session: str = Depends(require_session)) -> ClipsView:
    del session
    return ClipsView.model_validate(job_repository().clips_view(job_id))


@router.patch("/clips/{clip_id}", response_model=ClipView)
def patch_clip(
    clip_id: UUID,
    body: PatchClip,
    session: SessionDep,
    repo: RepoDep,
    if_match: str | None = Header(default=None, alias="If-Match"),
    ack: bool = False,
) -> ClipView:
    del session
    if if_match is None:
        raise ApiError("stale_write", "If-Match is required", 412)
    fields = set(body.model_fields_set)
    result = repo.patch_clip_content(
        clip_id,
        expected_etag=if_match,
        fields=fields,
        title=body.title,
        summary=body.summary,
        scene_caption=body.scene_caption,
        ack=ack,
        assemble_markdown=assemble_markdown,
    )
    match result["status"]:
        case "ok":
            return ClipView.model_validate(result["clip"])
        case "job_not_review_ready":
            raise ApiError("job_not_review_ready", "Job is not review-ready", 409)
        case "stale_write":
            raise ApiError("stale_write", "Clip ETag is stale", 412)
        case "needs_ack":
            raise ApiError("needs_ack", "Clip change needs acknowledgement", 409)
        case _:
            raise RuntimeError(f"unknown patch result: {result['status']}")
