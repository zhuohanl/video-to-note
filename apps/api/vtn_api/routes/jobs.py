from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from vtn_core.models import PromptDepth

from vtn_api.auth import require_session
from vtn_api.deps import job_repository, queue_provider
from vtn_api.errors import ApiError
from vtn_api.schemas import CreateJob, CreateJobResponse, JobView

router = APIRouter()


@router.post("/jobs", response_model=CreateJobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_job(
    body: CreateJob,
    request: Request,
    session: str = Depends(require_session),
) -> CreateJobResponse:
    del session
    if body.depth is PromptDepth.custom and not body.custom_prompt:
        raise ApiError("validation_error", "custom_prompt is required when depth is custom", 422)

    submission = job_repository().create_submission(
        url=body.url,
        depth=body.depth,
        custom_prompt=body.custom_prompt,
        examples=body.examples,
        use_saved_style=body.use_saved_style,
    )
    queue_provider(request).send({"job_id": str(submission.job_id), "attempt": 0})
    return CreateJobResponse(job_id=submission.job_id, cost_estimate=submission.cost_estimate)


@router.get("/jobs/{job_id}", response_model=JobView)
def get_job(job_id: UUID, session: str = Depends(require_session)) -> JobView:
    del session
    row = job_repository().get_job_view(job_id)
    if row is None:
        raise ApiError("version_not_found", "Job not found", 404)
    return JobView.model_validate(row)
