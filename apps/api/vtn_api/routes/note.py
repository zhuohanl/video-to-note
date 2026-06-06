from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from vtn_api.auth import require_session
from vtn_api.deps import job_repository
from vtn_api.errors import ApiError
from vtn_api.schemas import NoteView

router = APIRouter()


@router.get("/jobs/{job_id}/note", response_model=NoteView)
def get_note(job_id: UUID, session: str = Depends(require_session)) -> NoteView:
    del session
    row = job_repository().note_view(job_id)
    if row is None:
        raise ApiError("version_not_found", "Note not found", 404)
    return NoteView.model_validate(row)
