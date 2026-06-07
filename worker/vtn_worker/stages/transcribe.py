from __future__ import annotations

import asyncio

from vtn_transcript.chain import FakeTranscriptProvider

from vtn_worker.runner import StageContext
from vtn_worker.stages.shared_artifact import run_video_artifact


async def transcribe(
    context: StageContext,
    provider: FakeTranscriptProvider | None = None,
) -> None:
    transcript_provider = provider or FakeTranscriptProvider()
    video_id = context.repo.get_job_video_id(context.job_id)

    async def build() -> None:
        result = transcript_provider.fetch(video_id)
        spans = [
            {
                "start_sec": span.start_sec,
                "end_sec": span.end_sec,
                "text": span.text,
                "speaker": span.speaker,
            }
            for span in result.spans
        ]
        await asyncio.to_thread(
            context.repo.replace_transcript_spans,
            video_id,
            spans,
            result.source,
        )
        if result.warning is not None:
            code, message = result.warning
            context.repo.emit_event(context.job_id, "warning", {"code": code, "message": message})

    if context.repo.transcript_span_rows(video_id):
        return

    await run_video_artifact(context, video_id, "transcript", build)
