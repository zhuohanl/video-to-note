from __future__ import annotations

from vtn_core.models import JobStage, JobStatus

LEGAL_STAGE_TRANSITIONS: dict[JobStage, set[JobStage]] = {
    JobStage.queued: {JobStage.resolving},
    JobStage.resolving: {JobStage.acquiring_media},
    JobStage.acquiring_media: {JobStage.analyzing},
    JobStage.analyzing: {JobStage.segmenting},
    JobStage.segmenting: {JobStage.drafting},
    JobStage.drafting: set(),
}

LEGAL_STATUS_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.active: {JobStatus.review_ready, JobStatus.failed, JobStatus.canceled},
    JobStatus.review_ready: {JobStatus.exported, JobStatus.failed, JobStatus.canceled},
    JobStatus.exported: {JobStatus.failed, JobStatus.canceled},
    JobStatus.failed: set(),
    JobStatus.canceled: set(),
}


def legal_transition(from_stage: JobStage, to_stage: JobStage) -> bool:
    if to_stage in LEGAL_STAGE_TRANSITIONS[from_stage]:
        return True

    msg = f"illegal stage transition: {from_stage.value} -> {to_stage.value}"
    raise ValueError(msg)


def legal_status(from_status: JobStatus, to_status: JobStatus) -> bool:
    if to_status in LEGAL_STATUS_TRANSITIONS[from_status]:
        return True

    msg = f"illegal status transition: {from_status.value} -> {to_status.value}"
    raise ValueError(msg)
