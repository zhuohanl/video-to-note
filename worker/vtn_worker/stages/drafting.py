from __future__ import annotations

from vtn_notes.scene import SceneCandidate, choose_scene
from vtn_notes.summary import FakeSummaryGenerator

from vtn_worker.runner import StageContext


async def draft(
    context: StageContext,
    summary_generator: FakeSummaryGenerator | None = None,
) -> None:
    generator = summary_generator or FakeSummaryGenerator()
    video_id = context.repo.get_job_video_id(context.job_id)
    clips = context.repo.clip_rows(context.job_id)
    outline = "; ".join(str(clip["title"]) for clip in clips)

    for clip in clips:
        visuals = context.repo.visual_events_for_clip(video_id, clip["start_sec"], clip["end_sec"])
        candidates = [
            SceneCandidate(
                event["at_sec"],
                event["event_type"],
                event["confidence"],
                event["phash"],
                event["frame_blob_path"],
            )
            for event in visuals
            if event["frame_blob_path"]
        ]
        scene = choose_scene(candidates)
        summary = generator.summarize(
            title=str(clip["title"]),
            summary_seed=str(clip["summary_seed"]),
            outline=outline,
        )
        context.repo.update_clip_draft(
            clip_id=clip["id"],
            summary=summary,
            scene_at_sec=scene.at_sec,
            scene_blob_path=scene.frame_blob_path,
        )
        context.repo.emit_event(
            context.job_id,
            "clip.ready",
            {"clip_id": str(clip["id"]), "order_index": clip["order_index"]},
        )
