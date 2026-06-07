from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from vtn_export import build_export_zip
from vtn_storage.blob import BlobStore
from vtn_storage.repos import JobRepository

from vtn_api.auth import require_session
from vtn_api.deps import blob_store, job_repository
from vtn_api.schemas import ExportView

router = APIRouter()
SessionDep = Annotated[str, Depends(require_session)]
RepoDep = Annotated[JobRepository, Depends(job_repository)]
BlobDep = Annotated[BlobStore, Depends(blob_store)]


@router.post("/jobs/{job_id}/export", response_model=ExportView)
def export_job(
    job_id: UUID,
    session: SessionDep,
    repo: RepoDep,
    blobs: BlobDep,
) -> ExportView:
    del session
    context = repo.export_context(job_id)
    zip_bytes = build_export_zip(context, blobs)
    key = f"exports/{job_id}.zip"
    download_url = blobs.put(key, zip_bytes)
    repo.record_export(job_id, key)
    return ExportView(download_url=download_url)
