from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal, cast
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from vtn_core.models import Job, JobStage, JobStatus, PromptDepth, SourceType, TranscriptSource


@dataclass(frozen=True)
class JobSubmission:
    job_id: UUID
    cost_estimate: dict[str, Any]


ArtifactKind = Literal["proxy", "transcript", "visual"]

_ARTIFACT_COLUMNS: dict[ArtifactKind, tuple[str, str]] = {
    "proxy": ("proxy_state", "proxy_owner_job"),
    "transcript": ("transcript_state", "transcript_owner_job"),
    "visual": ("visual_state", "visual_owner_job"),
}


def event_channel(job_id: UUID) -> str:
    return f"vtn_job_{job_id.hex}"


class JobRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def create_video(self, source_url: str, source_type: SourceType) -> UUID:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO videos (source_url, source_type)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (source_url, source_type.value),
                )
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError("video insert returned no id")
                return cast(UUID, row[0])

    def create_job(self, video_id: UUID) -> UUID:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO jobs (video_id)
                    VALUES (%s)
                    RETURNING id
                    """,
                    (video_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError("job insert returned no id")
                return cast(UUID, row[0])

    def get_job(self, job_id: UUID) -> Job | None:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, video_id, stage, status, error_code, error_message,
                           attempt, created_at, updated_at
                    FROM jobs
                    WHERE id = %s
                    """,
                    (job_id,),
                )
                row: dict[str, Any] | None = cursor.fetchone()
                if row is None:
                    return None
                return Job.model_validate(row)

    def create_submission(
        self,
        *,
        url: str,
        depth: PromptDepth,
        custom_prompt: str | None,
        examples: list[dict[str, Any]],
        use_saved_style: bool,
    ) -> JobSubmission:
        cost_estimate = {"usd": "0.0500", "breakdown": {"profile": "fake_stub"}}
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO videos (source_url, source_type)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (url, SourceType.other.value),
                )
                video_row = cursor.fetchone()
                if video_row is None:
                    raise RuntimeError("video insert returned no id")
                video_id = cast(UUID, video_row[0])

                cursor.execute(
                    """
                    INSERT INTO jobs (video_id)
                    VALUES (%s)
                    RETURNING id
                    """,
                    (video_id,),
                )
                job_row = cursor.fetchone()
                if job_row is None:
                    raise RuntimeError("job insert returned no id")
                job_id = cast(UUID, job_row[0])

                cursor.execute(
                    """
                    INSERT INTO prompts (
                        job_id, depth, custom_prompt, examples, model_config
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        job_id,
                        depth.value,
                        custom_prompt,
                        Jsonb(examples),
                        Jsonb({"use_saved_style": use_saved_style}),
                    ),
                )
                cursor.execute(
                    """
                    INSERT INTO job_costs (job_id, estimate_usd, estimate_json, computed_at)
                    VALUES (%s, %s, %s, now())
                    """,
                    (job_id, Decimal("0.0500"), Jsonb(cost_estimate)),
                )
        return JobSubmission(job_id=job_id, cost_estimate=cost_estimate)

    def get_job_source_url(self, job_id: UUID) -> str:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT v.source_url
                    FROM jobs j
                    JOIN videos v ON v.id = j.video_id
                    WHERE j.id = %s
                    """,
                    (job_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError(f"job not found: {job_id}")
                return cast(str, row[0])

    def get_job_video_id(self, job_id: UUID) -> UUID:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT video_id FROM jobs WHERE id = %s", (job_id,))
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError(f"job not found: {job_id}")
                return cast(UUID, row[0])

    def claim_canonical_video(
        self,
        *,
        job_id: UUID,
        canonical_url: str,
        source_type: SourceType,
        title: str,
        duration_sec: Decimal,
    ) -> UUID:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT video_id
                    FROM jobs
                    WHERE id = %s
                    FOR UPDATE
                    """,
                    (job_id,),
                )
                job_row = cursor.fetchone()
                if job_row is None:
                    raise RuntimeError(f"job not found: {job_id}")
                placeholder_video_id = cast(UUID, job_row[0])

                cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (canonical_url,))
                cursor.execute(
                    "SELECT id FROM videos WHERE canonical_url = %s",
                    (canonical_url,),
                )
                canonical_row = cursor.fetchone()
                if canonical_row is not None:
                    canonical_video_id = cast(UUID, canonical_row[0])
                    if canonical_video_id != placeholder_video_id:
                        cursor.execute(
                            "UPDATE jobs SET video_id = %s, updated_at = now() WHERE id = %s",
                            (canonical_video_id, job_id),
                        )
                        cursor.execute(
                            """
                            DELETE FROM videos
                            WHERE id = %s
                              AND NOT EXISTS (
                                SELECT 1 FROM jobs WHERE video_id = %s
                              )
                            """,
                            (placeholder_video_id, placeholder_video_id),
                        )
                    return canonical_video_id

                cursor.execute(
                    """
                    UPDATE videos
                    SET canonical_url = %s,
                        source_type = %s,
                        title = %s,
                        duration_sec = %s,
                        artifacts_updated_at = now()
                    WHERE id = %s
                    """,
                    (
                        canonical_url,
                        source_type.value,
                        title,
                        duration_sec,
                        placeholder_video_id,
                    ),
                )
                return placeholder_video_id

    def proxy_blob_path(self, video_id: UUID) -> str | None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT proxy_blob_path FROM videos WHERE id = %s", (video_id,))
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError(f"video not found: {video_id}")
                return cast(str | None, row[0])

    def artifact_state(self, video_id: UUID, artifact: ArtifactKind) -> str:
        state_column, _ = _ARTIFACT_COLUMNS[artifact]
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT {state_column} FROM videos WHERE id = %s", (video_id,))
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError(f"video not found: {video_id}")
                return cast(str, row[0])

    def claim_artifact(self, video_id: UUID, job_id: UUID, artifact: ArtifactKind) -> bool:
        state_column, owner_column = _ARTIFACT_COLUMNS[artifact]
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    UPDATE videos
                    SET {state_column} = 'building',
                        {owner_column} = %s,
                        artifacts_updated_at = now()
                    WHERE id = %s AND {state_column} = 'absent'
                    RETURNING id
                    """,
                    (job_id, video_id),
                )
                return cursor.fetchone() is not None

    def reclaim_stale(
        self,
        video_id: UUID,
        job_id: UUID,
        artifact: ArtifactKind,
        *,
        stale_after: timedelta,
    ) -> bool:
        state_column, owner_column = _ARTIFACT_COLUMNS[artifact]
        stale_before = datetime.now(UTC) - stale_after
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    UPDATE videos
                    SET {owner_column} = %s,
                        artifacts_updated_at = now()
                    WHERE id = %s
                      AND {state_column} = 'building'
                      AND artifacts_updated_at < %s
                    RETURNING id
                    """,
                    (job_id, video_id, stale_before),
                )
                return cursor.fetchone() is not None

    def wait_ready(
        self,
        video_id: UUID,
        artifact: ArtifactKind,
        *,
        timeout_sec: float,
        poll_interval_sec: float,
    ) -> bool:
        import time

        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            state = self.artifact_state(video_id, artifact)
            if state == "ready":
                return True
            if state == "absent":
                return False
            time.sleep(poll_interval_sec)
        return self.artifact_state(video_id, artifact) == "ready"

    def release_on_fail(self, video_id: UUID, job_id: UUID, artifact: ArtifactKind) -> None:
        state_column, owner_column = _ARTIFACT_COLUMNS[artifact]
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    UPDATE videos
                    SET {state_column} = 'absent',
                        {owner_column} = NULL,
                        artifacts_updated_at = now()
                    WHERE id = %s
                      AND {state_column} = 'building'
                      AND {owner_column} = %s
                    """,
                    (video_id, job_id),
                )

    def set_proxy_ready(self, video_id: UUID, blob_path: str) -> None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE videos
                    SET proxy_blob_path = %s,
                        proxy_state = 'ready',
                        artifacts_updated_at = now()
                    WHERE id = %s
                    """,
                    (blob_path, video_id),
                )

    def replace_transcript_spans(
        self,
        video_id: UUID,
        spans: list[dict[str, Any]],
        source: TranscriptSource,
    ) -> None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM transcript_spans WHERE video_id = %s", (video_id,))
                cursor.executemany(
                    """
                    INSERT INTO transcript_spans (
                        video_id, start_sec, end_sec, text, speaker, source
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            video_id,
                            span["start_sec"],
                            span["end_sec"],
                            span["text"],
                            span["speaker"],
                            source.value,
                        )
                        for span in spans
                    ],
                )
                cursor.execute(
                    """
                    UPDATE videos
                    SET transcript_state = 'ready', artifacts_updated_at = now()
                    WHERE id = %s
                    """,
                    (video_id,),
                )

    def replace_visual_events(self, video_id: UUID, events: list[dict[str, Any]]) -> None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM visual_events WHERE video_id = %s", (video_id,))
                cursor.executemany(
                    """
                    INSERT INTO visual_events (
                        video_id, at_sec, event_type, confidence,
                        ocr_text, phash, frame_blob_path
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            video_id,
                            event["at_sec"],
                            event["event_type"],
                            event["confidence"],
                            event["ocr_text"],
                            event["phash"],
                            event["frame_blob_path"],
                        )
                        for event in events
                    ],
                )
                cursor.execute(
                    """
                    UPDATE videos
                    SET visual_state = 'ready', artifacts_updated_at = now()
                    WHERE id = %s
                    """,
                    (video_id,),
                )

    def transcript_span_rows(self, video_id: UUID) -> list[dict[str, Any]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT start_sec, end_sec, text, speaker, source
                    FROM transcript_spans
                    WHERE video_id = %s
                    ORDER BY start_sec
                    """,
                    (video_id,),
                )
                return list(cursor.fetchall())

    def visual_event_rows(self, video_id: UUID) -> list[dict[str, Any]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT at_sec, event_type, confidence, ocr_text, phash, frame_blob_path
                    FROM visual_events
                    WHERE video_id = %s
                    ORDER BY at_sec
                    """,
                    (video_id,),
                )
                return list(cursor.fetchall())

    def replace_clips(self, job_id: UUID, clips: list[dict[str, Any]]) -> None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM clips WHERE job_id = %s", (job_id,))
                cursor.executemany(
                    """
                    INSERT INTO clips (
                        job_id, order_index, start_sec, end_sec, title,
                        summary_seed, classification, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
                    """,
                    [
                        (
                            job_id,
                            index,
                            clip["start_sec"],
                            clip["end_sec"],
                            clip["title"],
                            clip["summary_seed"],
                            clip["classification"],
                        )
                        for index, clip in enumerate(clips)
                    ],
                )

    def clip_rows(self, job_id: UUID) -> list[dict[str, Any]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, order_index, start_sec, end_sec, title, summary_seed,
                           classification
                    FROM clips
                    WHERE job_id = %s
                    ORDER BY order_index
                    """,
                    (job_id,),
                )
                return list(cursor.fetchall())

    def visual_events_for_clip(
        self,
        video_id: UUID,
        start_sec: Decimal,
        end_sec: Decimal,
    ) -> list[dict[str, Any]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT at_sec, event_type, confidence, ocr_text, phash, frame_blob_path
                    FROM visual_events
                    WHERE video_id = %s AND at_sec >= %s AND at_sec <= %s
                    ORDER BY at_sec
                    """,
                    (video_id, start_sec, end_sec),
                )
                return list(cursor.fetchall())

    def update_clip_draft(
        self,
        *,
        clip_id: UUID,
        summary: str,
        scene_at_sec: Decimal,
        scene_blob_path: str,
    ) -> None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE clips
                    SET summary = %s,
                        ai_summary = %s,
                        status = 'ready',
                        scene_at_sec = %s,
                        scene_blob_path = %s,
                        scene_source = 'auto',
                        updated_at = now()
                    WHERE id = %s
                    """,
                    (summary, summary, scene_at_sec, scene_blob_path, clip_id),
                )

    def drafted_clip_rows(self, job_id: UUID) -> list[dict[str, Any]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, order_index, start_sec, end_sec, title, summary,
                           scene_at_sec, scene_blob_path, scene_caption, scene_source,
                           needs_regen
                    FROM clips
                    WHERE job_id = %s
                    ORDER BY order_index
                    """,
                    (job_id,),
                )
                return list(cursor.fetchall())

    def clips_view(self, job_id: UUID) -> dict[str, Any]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, order_index, start_sec, end_sec, title, summary,
                           scene_caption, status, scene_at_sec, scene_blob_path,
                           scene_source, needs_regen, updated_at
                    FROM clips
                    WHERE job_id = %s
                    ORDER BY order_index
                    """,
                    (job_id,),
                )
                rows = list(cursor.fetchall())

        clips = []
        etags = []
        for row in rows:
            etag = f'"{row["updated_at"].isoformat()}"'
            etags.append(etag)
            scene_blob_path = row["scene_blob_path"]
            clips.append(
                {
                    "id": row["id"],
                    "order_index": row["order_index"],
                    "start_sec": row["start_sec"],
                    "end_sec": row["end_sec"],
                    "title": row["title"],
                    "summary": row["summary"],
                    "scene_caption": row["scene_caption"],
                    "status": row["status"],
                    "scene_at_sec": row["scene_at_sec"],
                    "scene_url": f"local://{scene_blob_path}" if scene_blob_path else None,
                    "scene_source": row["scene_source"],
                    "needs_regen": row["needs_regen"],
                    "etag": etag,
                }
            )
        return {"clips": clips, "collection_etag": max(etags) if etags else '""'}

    def note_view(self, job_id: UUID) -> dict[str, Any] | None:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT markdown, include_summary, include_transcript,
                           is_polished, clips_dirty, updated_at
                    FROM notes
                    WHERE job_id = %s
                    """,
                    (job_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
        return {
            "markdown": row["markdown"],
            "include_summary": row["include_summary"],
            "include_transcript": row["include_transcript"],
            "is_polished": row["is_polished"],
            "clips_dirty": row["clips_dirty"],
            "etag": f'"{row["updated_at"].isoformat()}"',
        }

    def create_initial_note(self, job_id: UUID, markdown: str, clips: list[dict[str, Any]]) -> None:
        snapshot = [
            {
                "id": str(clip["id"]),
                "order_index": clip["order_index"],
                "start_sec": str(clip["start_sec"]),
                "end_sec": str(clip["end_sec"]),
                "title": clip["title"],
                "summary": clip["summary"],
                "scene_at_sec": str(clip["scene_at_sec"]),
                "scene_blob_path": clip["scene_blob_path"],
                "scene_caption": clip["scene_caption"],
                "scene_source": clip["scene_source"],
                "needs_regen": clip["needs_regen"],
            }
            for clip in clips
        ]
        settings = {
            "is_polished": False,
            "include_summary": True,
            "include_transcript": False,
        }
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO notes (
                        job_id, markdown, include_summary, include_transcript,
                        is_polished, clips_dirty, built_from_version
                    )
                    VALUES (%s, %s, true, false, false, false, 1)
                    ON CONFLICT (job_id) DO UPDATE
                    SET markdown = EXCLUDED.markdown,
                        include_summary = true,
                        include_transcript = false,
                        is_polished = false,
                        clips_dirty = false,
                        built_from_version = 1,
                        updated_at = now()
                    """,
                    (job_id, markdown),
                )
                cursor.execute(
                    """
                    INSERT INTO note_versions (
                        job_id, seq, label, kind, is_baseline,
                        note_markdown, note_settings, clips_snapshot
                    )
                    VALUES (%s, 1, 'v1', 'initial', true, %s, %s, %s)
                    ON CONFLICT (job_id, seq) DO NOTHING
                    """,
                    (job_id, markdown, Jsonb(settings), Jsonb(snapshot)),
                )

    def get_job_view(self, job_id: UUID) -> dict[str, Any] | None:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT j.id, j.status, j.stage, j.error_code, j.error_message,
                           n.is_polished, n.clips_dirty,
                           c.estimate_usd, c.estimate_json
                    FROM jobs j
                    LEFT JOIN notes n ON n.job_id = j.id
                    LEFT JOIN job_costs c ON c.job_id = j.id
                    WHERE j.id = %s
                    """,
                    (job_id,),
                )
                row: dict[str, Any] | None = cursor.fetchone()
                if row is None:
                    return None

        estimate_usd = row["estimate_usd"]
        estimate_json = row["estimate_json"] or {}
        cost: dict[str, Any] = {}
        if estimate_usd is not None:
            cost["estimate_usd"] = f"{estimate_usd:.4f}"
        if estimate_json:
            cost["estimate"] = estimate_json

        is_polished = bool(row["is_polished"]) if row["is_polished"] is not None else False
        clips_dirty = bool(row["clips_dirty"]) if row["clips_dirty"] is not None else False

        return {
            "id": row["id"],
            "status": row["status"],
            "stage": row["stage"],
            "flags": {
                "is_polished": is_polished,
                "clips_dirty": clips_dirty,
            },
            "error_code": row["error_code"],
            "error_message": row["error_message"],
            "cost": cost,
        }

    def emit_event(self, job_id: UUID, type: str, payload: dict[str, Any]) -> int:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO job_events (job_id, type, payload)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (job_id, type, Jsonb(payload)),
                )
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError("event insert returned no id")
                event_id = cast(int, row[0])
                cursor.execute("SELECT pg_notify(%s, %s)", (event_channel(job_id), str(event_id)))
                return event_id

    def list_events_after(self, job_id: UUID, last_event_id: int) -> list[dict[str, Any]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, job_id, type, payload
                    FROM job_events
                    WHERE job_id = %s AND id > %s
                    ORDER BY id
                    """,
                    (job_id, last_event_id),
                )
                return list(cursor.fetchall())

    def update_job_stage(self, job_id: UUID, stage: JobStage) -> None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE jobs
                    SET stage = %s, updated_at = now()
                    WHERE id = %s
                    """,
                    (stage.value, job_id),
                )

    def mark_review_ready(self, job_id: UUID) -> None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE jobs
                    SET status = %s, updated_at = now()
                    WHERE id = %s
                    """,
                    (JobStatus.review_ready.value, job_id),
                )

    def fail_job(self, job_id: UUID, code: str, message: str) -> None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE jobs
                    SET status = %s, error_code = %s, error_message = %s, updated_at = now()
                    WHERE id = %s
                    """,
                    (JobStatus.failed.value, code, message, job_id),
                )
