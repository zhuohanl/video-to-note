from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import ValidationError
from vtn_notes.assemble import assemble_markdown
from vtn_storage.repos import JobRepository

from vtn_api.auth import require_session
from vtn_api.deps import job_repository
from vtn_api.errors import ApiError
from vtn_api.schemas import NoteView, PatchNote, PutNote

router = APIRouter()
SessionDep = Annotated[str, Depends(require_session)]
RepoDep = Annotated[JobRepository, Depends(job_repository)]


@router.get("/jobs/{job_id}/note", response_model=NoteView)
def get_note(job_id: UUID, session: str = Depends(require_session)) -> NoteView:
    del session
    row = job_repository().note_view(job_id)
    if row is None:
        raise ApiError("version_not_found", "Note not found", 404)
    return NoteView.model_validate(row)


@router.put("/jobs/{job_id}/note", response_model=NoteView)
def put_note(
    job_id: UUID,
    body: PutNote,
    session: SessionDep,
    repo: RepoDep,
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> NoteView:
    del session
    if if_match is None:
        raise ApiError("stale_write", "If-Match is required", 412)
    result = repo.put_note_markdown(job_id, expected_etag=if_match, markdown=body.markdown)
    return _note_write_response(result)


@router.patch("/jobs/{job_id}/note", response_model=NoteView)
def patch_note(
    job_id: UUID,
    raw_body: dict[str, object],
    session: SessionDep,
    repo: RepoDep,
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> NoteView:
    del session
    if if_match is None:
        raise ApiError("stale_write", "If-Match is required", 412)
    try:
        body = PatchNote.model_validate(raw_body)
    except ValidationError as exc:
        message = "include_summary or include_transcript must be true"
        raise ApiError("validation_error", message, 422) from exc
    result = repo.patch_note_flags(
        job_id,
        expected_etag=if_match,
        fields=set(body.model_fields_set),
        include_summary=body.include_summary,
        include_transcript=body.include_transcript,
    )
    return _note_write_response(result)


@router.post("/jobs/{job_id}/note/rebuild", response_model=NoteView)
def rebuild_note(
    job_id: UUID,
    session: SessionDep,
    repo: RepoDep,
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> NoteView:
    del session
    if if_match is None:
        raise ApiError("stale_write", "If-Match is required", 412)
    result = repo.rebuild_note(job_id, expected_etag=if_match, assemble_markdown=assemble_markdown)
    return _note_write_response(result)


@router.post("/jobs/{job_id}/note/keep", response_model=NoteView)
def keep_note(
    job_id: UUID,
    session: SessionDep,
    repo: RepoDep,
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> NoteView:
    del session
    if if_match is None:
        raise ApiError("stale_write", "If-Match is required", 412)
    result = repo.keep_note(job_id, expected_etag=if_match)
    return _note_write_response(result)


def _note_write_response(result: dict[str, object]) -> NoteView:
    match result["status"]:
        case "ok":
            return NoteView.model_validate(result["note"])
        case "stale_write":
            raise ApiError("stale_write", "Note ETag is stale", 412)
        case "validation_error":
            message = "include_summary or include_transcript must be true"
            raise ApiError("validation_error", message, 422)
        case _:
            raise RuntimeError(f"unknown note write result: {result['status']}")
