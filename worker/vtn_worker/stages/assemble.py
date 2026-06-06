from __future__ import annotations

from vtn_notes.assemble import assemble_markdown

from vtn_worker.runner import StageContext


async def assemble_initial_note(context: StageContext) -> None:
    clips = context.repo.drafted_clip_rows(context.job_id)
    markdown = assemble_markdown(clips)
    context.repo.create_initial_note(context.job_id, markdown, clips)
    context.repo.mark_review_ready(context.job_id)
    context.repo.emit_event(context.job_id, "done", {})
