from __future__ import annotations

from decimal import Decimal

from vtn_segment.refine import CandidateClip, FakeRefiner, RefinementError, fallback_refine

from vtn_worker.runner import StageContext


def _candidate_clips(duration_sec: Decimal) -> list[CandidateClip]:
    midpoint = Decimal("14.000") if duration_sec >= Decimal("28.000") else duration_sec / 2
    return [
        CandidateClip(Decimal("0.000"), midpoint),
        CandidateClip(midpoint, duration_sec),
    ]


async def segment(context: StageContext, refiner: FakeRefiner | None = None) -> None:
    video_id = context.repo.get_job_video_id(context.job_id)
    spans = context.repo.transcript_span_rows(video_id)
    context.repo.visual_event_rows(video_id)
    duration_sec = max((span["end_sec"] for span in spans), default=Decimal("0.000"))
    candidates = _candidate_clips(duration_sec)

    segment_refiner = refiner or FakeRefiner()
    try:
        refined = segment_refiner.refine(candidates)
    except RefinementError:
        refined = fallback_refine(candidates)
        context.repo.emit_event(
            context.job_id,
            "warning",
            {
                "code": "refinement_fallback",
                "message": "Using deterministic segment boundaries",
            },
        )

    context.repo.replace_clips(
        context.job_id,
        [
            {
                "start_sec": clip.start_sec,
                "end_sec": clip.end_sec,
                "title": clip.title,
                "summary_seed": clip.summary_seed,
                "classification": clip.classification.value,
            }
            for clip in refined
        ],
    )
