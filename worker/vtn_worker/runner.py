from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

from vtn_core.models import JobStage, JobStatus
from vtn_storage.repos import JobRepository

StageFn = Callable[["StageContext"], Awaitable[None]]


@dataclass(frozen=True)
class StageContext:
    job_id: UUID
    attempt: int
    stage: str
    repo: JobRepository


class PipelineError(Exception):
    def __init__(self, code: str, message: str, stage: str) -> None:
        self.code = code
        self.message = message
        self.stage = stage
        super().__init__(message)


async def _noop(context: StageContext) -> None:
    del context


async def _mark_done(context: StageContext) -> None:
    context.repo.mark_review_ready(context.job_id)
    context.repo.emit_event(context.job_id, "done", {})


@dataclass(frozen=True)
class StageHandlers:
    resolving: StageFn = _noop
    acquiring_media: StageFn = _noop
    transcribe: StageFn = _noop
    index_visual: StageFn = _noop
    extract_style: StageFn = _noop
    segmenting: StageFn = _noop
    drafting: StageFn = _noop
    assemble: StageFn = _mark_done


async def _run_linear_stage(
    repo: JobRepository,
    job_id: UUID,
    attempt: int,
    stage: JobStage,
    handler: StageFn,
) -> None:
    repo.update_job_stage(job_id, stage)
    repo.emit_event(job_id, "stage", {"stage": stage.value})
    await handler(StageContext(job_id=job_id, attempt=attempt, stage=stage.value, repo=repo))


async def _run_branch(
    repo: JobRepository,
    job_id: UUID,
    attempt: int,
    stage: str,
    handler: StageFn,
) -> None:
    repo.emit_event(job_id, "stage", {"stage": stage})
    await handler(StageContext(job_id=job_id, attempt=attempt, stage=stage, repo=repo))


async def run(
    job_id: UUID,
    *,
    attempt: int,
    repo: JobRepository,
    stages: StageHandlers | None = None,
) -> None:
    job = repo.get_job(job_id)
    if job is None:
        raise PipelineError("job_not_found", "Job was not found", "queued")
    if job.status != JobStatus.active:
        return

    handlers = stages or StageHandlers()
    await _run_linear_stage(repo, job_id, attempt, JobStage.resolving, handlers.resolving)
    await _run_linear_stage(
        repo,
        job_id,
        attempt,
        JobStage.acquiring_media,
        handlers.acquiring_media,
    )

    repo.update_job_stage(job_id, JobStage.analyzing)
    repo.emit_event(job_id, "stage", {"stage": JobStage.analyzing.value})
    await asyncio.gather(
        _run_branch(repo, job_id, attempt, "transcribe", handlers.transcribe),
        _run_branch(repo, job_id, attempt, "index visual", handlers.index_visual),
        _run_branch(repo, job_id, attempt, "extract style", handlers.extract_style),
    )

    await _run_linear_stage(repo, job_id, attempt, JobStage.segmenting, handlers.segmenting)
    await _run_linear_stage(repo, job_id, attempt, JobStage.drafting, handlers.drafting)
    await handlers.assemble(
        StageContext(job_id=job_id, attempt=attempt, stage="review_ready", repo=repo)
    )
    repo.record_actual_costs(job_id)
