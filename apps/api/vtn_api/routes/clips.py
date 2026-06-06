from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from vtn_api.auth import require_session
from vtn_api.deps import job_repository
from vtn_api.schemas import ClipsView

router = APIRouter()


@router.get("/jobs/{job_id}/clips", response_model=ClipsView)
def get_clips(job_id: UUID, session: str = Depends(require_session)) -> ClipsView:
    del session
    return ClipsView.model_validate(job_repository().clips_view(job_id))
