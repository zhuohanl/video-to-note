from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal, cast
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from vtn_core.cost import actual_from_usage, estimate
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


def _etag(value: Any) -> str:
    return f'"{value.isoformat()}"'


def _clip_snapshot(clips: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": str(clip["id"]),
            "order_index": clip["order_index"],
            "start_sec": str(clip["start_sec"]),
            "end_sec": str(clip["end_sec"]),
            "title": clip["title"],
            "summary": clip["summary"],
            "scene_at_sec": str(clip["scene_at_sec"]) if clip["scene_at_sec"] is not None else None,
            "scene_blob_path": clip["scene_blob_path"],
            "scene_caption": clip["scene_caption"],
            "scene_source": clip["scene_source"],
            "needs_regen": clip["needs_regen"],
        }
        for clip in clips
    ]


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
        cost_estimate = estimate(None, depth)
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
                    (job_id, Decimal(str(cost_estimate["usd"])), Jsonb(cost_estimate)),
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

    def get_prompt(self, job_id: UUID) -> dict[str, Any]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT depth, custom_prompt, examples, style_profile,
                           save_style_as_default, model_config
                    FROM prompts
                    WHERE job_id = %s
                    """,
                    (job_id,),
                )
                row: dict[str, Any] | None = cursor.fetchone()
                if row is None:
                    raise RuntimeError(f"prompt not found: {job_id}")
                return dict(row)

    def set_style_profile(self, job_id: UUID, profile: dict[str, Any]) -> None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE prompts
                    SET style_profile = %s
                    WHERE job_id = %s
                    """,
                    (Jsonb(profile), job_id),
                )

    def upsert_style_default(
        self,
        examples: list[dict[str, Any]],
        extracted: dict[str, Any],
    ) -> None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO style_defaults (id, examples, extracted, updated_at)
                    VALUES (true, %s, %s, now())
                    ON CONFLICT (id)
                    DO UPDATE SET examples = EXCLUDED.examples,
                                  extracted = EXCLUDED.extracted,
                                  updated_at = now()
                    """,
                    (Jsonb(examples), Jsonb(extracted)),
                )

    def cost_row(self, job_id: UUID) -> dict[str, Any]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT estimate_usd, estimate_json, actual_usd, actual_json
                    FROM job_costs
                    WHERE job_id = %s
                    """,
                    (job_id,),
                )
                row: dict[str, Any] | None = cursor.fetchone()
                if row is None:
                    raise RuntimeError(f"cost row not found: {job_id}")
                return dict(row)

    def update_cost_estimate(self, job_id: UUID, cost_estimate: dict[str, Any]) -> None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE job_costs
                    SET estimate_usd = %s,
                        estimate_json = %s,
                        computed_at = now()
                    WHERE job_id = %s
                    """,
                    (Decimal(str(cost_estimate["usd"])), Jsonb(cost_estimate), job_id),
                )

    def record_actual_costs(self, job_id: UUID) -> None:
        job = self.get_job(job_id)
        if job is None:
            raise RuntimeError(f"job not found: {job_id}")
        video_id = job.video_id
        spans = self.transcript_span_rows(video_id)
        visuals = self.visual_event_rows(video_id)
        clips = self.clips_view(job_id)["clips"]
        transcript_end_sec = max((row["end_sec"] for row in spans), default=Decimal("0.000"))
        actual = actual_from_usage(
            transcript_end_sec=transcript_end_sec,
            ocr_frames=len(visuals),
            clip_count=len(clips),
        )
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE job_costs
                    SET actual_usd = %s,
                        actual_json = %s,
                        computed_at = now()
                    WHERE job_id = %s
                    """,
                    (Decimal(str(actual["usd"])), Jsonb(actual), job_id),
                )

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

    def video_proxy_key(self, video_id: UUID) -> str:
        path = self.proxy_blob_path(video_id)
        if path is None:
            raise RuntimeError(f"proxy not ready for video: {video_id}")
        return path

    def clip_media_context(self, clip_id: UUID) -> dict[str, Any]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT c.id, c.job_id, c.start_sec, c.end_sec, c.updated_at,
                           j.video_id, j.status
                    FROM clips c
                    JOIN jobs j ON j.id = c.job_id
                    WHERE c.id = %s
                    """,
                    (clip_id,),
                )
                row: dict[str, Any] | None = cursor.fetchone()
                if row is None:
                    raise RuntimeError(f"clip not found: {clip_id}")
                return dict(row)

    def scene_candidates(self, clip_id: UUID, limit: int = 5) -> list[dict[str, Any]]:
        context = self.clip_media_context(clip_id)
        rows = self.visual_events_for_clip(
            context["video_id"],
            context["start_sec"],
            context["end_sec"],
        )
        return sorted(rows, key=lambda row: row["confidence"], reverse=True)[:limit]

    def set_manual_scene(
        self,
        clip_id: UUID,
        *,
        expected_etag: str,
        at_sec: Decimal,
        scene_blob_path: str,
    ) -> dict[str, Any]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT updated_at
                    FROM clips
                    WHERE id = %s
                    FOR UPDATE
                    """,
                    (clip_id,),
                )
                row: dict[str, Any] | None = cursor.fetchone()
                if row is None:
                    raise RuntimeError(f"clip not found: {clip_id}")
                current_etag = _etag(row["updated_at"])
                if current_etag != expected_etag:
                    return {"stale": True, "etag": current_etag}
                cursor.execute(
                    """
                    UPDATE clips
                    SET scene_at_sec = %s,
                        scene_blob_path = %s,
                        scene_source = 'manual',
                        updated_at = now()
                    WHERE id = %s
                    RETURNING updated_at
                    """,
                    (at_sec, scene_blob_path, clip_id),
                )
                updated = cursor.fetchone()
                if updated is None:
                    raise RuntimeError(f"clip update failed: {clip_id}")
                return {
                    "stale": False,
                    "etag": _etag(updated["updated_at"]),
                    "scene_at_sec": at_sec,
                    "scene_blob_path": scene_blob_path,
                    "scene_source": "manual",
                }

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

    def patch_clip_content(
        self,
        clip_id: UUID,
        *,
        expected_etag: str,
        fields: set[str],
        title: str | None = None,
        summary: str | None = None,
        scene_caption: str | None = None,
        ack: bool = False,
        assemble_markdown: Callable[[list[dict[str, Any]]], str],
    ) -> dict[str, Any]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT c.id, c.job_id, c.updated_at, c.summary, c.ai_summary,
                           j.status
                    FROM clips c
                    JOIN jobs j ON j.id = c.job_id
                    WHERE c.id = %s
                    FOR UPDATE OF c, j
                    """,
                    (clip_id,),
                )
                clip: dict[str, Any] | None = cursor.fetchone()
                if clip is None:
                    raise RuntimeError(f"clip not found: {clip_id}")
                if clip["status"] not in {JobStatus.review_ready.value, JobStatus.exported.value}:
                    return {"status": "job_not_review_ready"}

                current_etag = _etag(clip["updated_at"])
                if current_etag != expected_etag:
                    return {"status": "stale_write", "etag": current_etag}

                cursor.execute(
                    """
                    SELECT markdown, include_summary, include_transcript,
                           is_polished, clips_dirty
                    FROM notes
                    WHERE job_id = %s
                    FOR UPDATE
                    """,
                    (clip["job_id"],),
                )
                note: dict[str, Any] | None = cursor.fetchone()
                if note is None:
                    raise RuntimeError(f"note not found for job: {clip['job_id']}")
                if note["is_polished"] and not ack:
                    return {"status": "needs_ack"}
                if note["is_polished"]:
                    self._freeze_version(cursor, clip["job_id"], "auto_pre_change", note)

                assignments = ["updated_at = now()"]
                values: list[Any] = []
                if "title" in fields:
                    assignments.append("title = %s")
                    values.append(title)
                if "summary" in fields:
                    restored_summary = clip["ai_summary"] if summary is None else summary
                    if summary is not None and clip["ai_summary"] is None:
                        assignments.append("ai_summary = %s")
                        values.append(clip["summary"])
                    assignments.append("summary = %s")
                    values.append(restored_summary)
                if "scene_caption" in fields:
                    assignments.append("scene_caption = %s")
                    values.append(scene_caption)

                values.append(clip_id)
                cursor.execute(
                    f"""
                    UPDATE clips
                    SET {", ".join(assignments)}
                    WHERE id = %s
                    RETURNING id, job_id, order_index, start_sec, end_sec, title, summary,
                              scene_caption, status, scene_at_sec, scene_blob_path,
                              scene_source, needs_regen, updated_at
                    """,
                    values,
                )
                updated: dict[str, Any] | None = cursor.fetchone()
                if updated is None:
                    raise RuntimeError(f"clip update failed: {clip_id}")

                if note["is_polished"]:
                    cursor.execute(
                        """
                        UPDATE notes
                        SET clips_dirty = true,
                            updated_at = now()
                        WHERE job_id = %s
                        """,
                        (clip["job_id"],),
                    )
                else:
                    rows = self._drafted_clip_rows(cursor, clip["job_id"])
                    cursor.execute(
                        """
                        UPDATE notes
                        SET markdown = %s,
                            is_polished = false,
                            clips_dirty = false,
                            updated_at = now()
                        WHERE job_id = %s
                        """,
                        (assemble_markdown(rows), clip["job_id"]),
                    )

        return {"status": "ok", "clip": self._clip_view_from_row(updated)}

    def split_clip(
        self,
        clip_id: UUID,
        *,
        expected_collection_etag: str,
        at_sec: Decimal,
        ack: bool = False,
        split_values: Callable[[dict[str, Any], Decimal], tuple[dict[str, Any], dict[str, Any]]],
        assemble_markdown: Callable[[list[dict[str, Any]]], str],
    ) -> dict[str, Any]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                context = self._structural_context_for_clip(cursor, clip_id)
                if context["status"] != "ok":
                    return context
                source = next(clip for clip in context["clips"] if clip["id"] == clip_id)
                if not (source["start_sec"] < at_sec < source["end_sec"]):
                    return {
                        "status": "validation_error",
                        "message": "Split point must be inside clip",
                    }
                if context["collection_etag"] != expected_collection_etag:
                    return {"status": "stale_write", "etag": context["collection_etag"]}
                note = self._locked_note(cursor, context["job_id"])
                if note["is_polished"] and not ack:
                    return {"status": "needs_ack"}
                if note["is_polished"]:
                    self._freeze_version(cursor, context["job_id"], "auto_pre_change", note)

                first, second = split_values(source, at_sec)
                cursor.execute(
                    """
                    UPDATE clips
                    SET order_index = order_index + 1000
                    WHERE job_id = %s AND order_index > %s
                    """,
                    (context["job_id"], source["order_index"]),
                )
                self._update_clip_placeholder(cursor, clip_id, first)
                cursor.execute(
                    """
                    INSERT INTO clips (
                        job_id, order_index, start_sec, end_sec, title, summary_seed,
                        summary, ai_summary, classification, confidence, status,
                        scene_at_sec, scene_blob_path, scene_caption, scene_source,
                        needs_regen
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true
                    )
                    """,
                    (
                        context["job_id"],
                        source["order_index"] + 1,
                        second["start_sec"],
                        second["end_sec"],
                        second["title"],
                        second["summary_seed"],
                        second["summary"],
                        second["ai_summary"],
                        second["classification"],
                        second["confidence"],
                        second["status"],
                        second["scene_at_sec"],
                        second["scene_blob_path"],
                        second["scene_caption"],
                        second["scene_source"],
                    ),
                )
                cursor.execute(
                    """
                    UPDATE clips
                    SET order_index = order_index - 999,
                        updated_at = now()
                    WHERE job_id = %s AND order_index >= 1000
                    """,
                    (context["job_id"],),
                )
                self._complete_clip_mutation(cursor, context["job_id"], note, assemble_markdown)

        return {"status": "ok", "clips": self.clips_view(context["job_id"])}

    def merge_clips(
        self,
        clip_ids: list[UUID],
        *,
        expected_collection_etag: str,
        ack: bool = False,
        merge_values: Callable[[list[dict[str, Any]]], dict[str, Any]],
        assemble_markdown: Callable[[list[dict[str, Any]]], str],
    ) -> dict[str, Any]:
        if not clip_ids:
            return {"status": "validation_error", "message": "clip_ids is required"}
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                context = self._structural_context_for_clip(cursor, clip_ids[0])
                if context["status"] != "ok":
                    return context
                by_id = {clip["id"]: clip for clip in context["clips"]}
                if any(clip_id not in by_id for clip_id in clip_ids):
                    return {"status": "validation_error", "message": "All clips must be in one job"}
                selected = sorted(
                    [by_id[clip_id] for clip_id in clip_ids],
                    key=lambda clip: clip["order_index"],
                )
                expected_indexes = list(
                    range(selected[0]["order_index"], selected[0]["order_index"] + len(selected))
                )
                if [clip["order_index"] for clip in selected] != expected_indexes:
                    return {
                        "status": "validation_error",
                        "message": "Merge clips must be consecutive",
                    }
                if context["collection_etag"] != expected_collection_etag:
                    return {"status": "stale_write", "etag": context["collection_etag"]}
                note = self._locked_note(cursor, context["job_id"])
                if note["is_polished"] and not ack:
                    return {"status": "needs_ack"}
                if note["is_polished"]:
                    self._freeze_version(cursor, context["job_id"], "auto_pre_change", note)

                merged = merge_values(selected)
                first_id = selected[0]["id"]
                self._update_clip_placeholder(cursor, first_id, merged)
                delete_ids = [clip["id"] for clip in selected[1:]]
                if delete_ids:
                    cursor.execute("DELETE FROM clips WHERE id = ANY(%s)", (delete_ids,))
                cursor.execute(
                    """
                    UPDATE clips
                    SET order_index = order_index - %s,
                        updated_at = now()
                    WHERE job_id = %s AND order_index > %s
                    """,
                    (len(selected) - 1, context["job_id"], selected[-1]["order_index"]),
                )
                self._complete_clip_mutation(cursor, context["job_id"], note, assemble_markdown)

        return {"status": "ok", "clips": self.clips_view(context["job_id"])}

    def regenerate_clip(
        self,
        clip_id: UUID,
        *,
        expected_etag: str,
        ack: bool = False,
        summary_generator: Callable[[dict[str, Any]], str],
        assemble_markdown: Callable[[list[dict[str, Any]]], str],
    ) -> dict[str, Any]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT c.id, c.job_id, c.updated_at, c.title, c.summary_seed,
                           j.status
                    FROM clips c
                    JOIN jobs j ON j.id = c.job_id
                    WHERE c.id = %s
                    FOR UPDATE OF c, j
                    """,
                    (clip_id,),
                )
                clip: dict[str, Any] | None = cursor.fetchone()
                if clip is None:
                    raise RuntimeError(f"clip not found: {clip_id}")
                if clip["status"] not in {JobStatus.review_ready.value, JobStatus.exported.value}:
                    return {"status": "job_not_review_ready"}
                current_etag = _etag(clip["updated_at"])
                if current_etag != expected_etag:
                    return {"status": "stale_write", "etag": current_etag}
                note = self._locked_note(cursor, clip["job_id"])
                if note["is_polished"] and not ack:
                    return {"status": "needs_ack"}
                if note["is_polished"]:
                    self._freeze_version(cursor, clip["job_id"], "auto_pre_change", note)

                summary = summary_generator(clip)
                cursor.execute(
                    """
                    UPDATE clips
                    SET summary = %s,
                        ai_summary = %s,
                        needs_regen = false,
                        updated_at = now()
                    WHERE id = %s
                    RETURNING id, job_id, order_index, start_sec, end_sec, title, summary,
                              scene_caption, status, scene_at_sec, scene_blob_path,
                              scene_source, needs_regen, updated_at
                    """,
                    (summary, summary, clip_id),
                )
                updated: dict[str, Any] | None = cursor.fetchone()
                if updated is None:
                    raise RuntimeError(f"clip update failed: {clip_id}")
                self._complete_clip_mutation(cursor, clip["job_id"], note, assemble_markdown)

        return {"status": "ok", "clip": self._clip_view_from_row(updated)}

    def _structural_context_for_clip(self, cursor: Any, clip_id: UUID) -> dict[str, Any]:
        cursor.execute(
            """
            SELECT c.job_id, j.status
            FROM clips c
            JOIN jobs j ON j.id = c.job_id
            WHERE c.id = %s
            FOR UPDATE OF j
            """,
            (clip_id,),
        )
        row: dict[str, Any] | None = cursor.fetchone()
        if row is None:
            raise RuntimeError(f"clip not found: {clip_id}")
        if row["status"] not in {JobStatus.review_ready.value, JobStatus.exported.value}:
            return {"status": "job_not_review_ready"}
        cursor.execute(
            """
            SELECT id, job_id, order_index, start_sec, end_sec, title, summary_seed,
                   summary, ai_summary, classification, confidence, status,
                   scene_at_sec, scene_blob_path, scene_caption, scene_source,
                   needs_regen, updated_at
            FROM clips
            WHERE job_id = %s
            ORDER BY order_index
            FOR UPDATE
            """,
            (row["job_id"],),
        )
        clips = list(cursor.fetchall())
        etags = [_etag(clip["updated_at"]) for clip in clips]
        return {
            "status": "ok",
            "job_id": row["job_id"],
            "clips": clips,
            "collection_etag": max(etags) if etags else '""',
        }

    def _locked_note(self, cursor: Any, job_id: UUID) -> dict[str, Any]:
        cursor.execute(
            """
            SELECT markdown, include_summary, include_transcript, is_polished, clips_dirty
            FROM notes
            WHERE job_id = %s
            FOR UPDATE
            """,
            (job_id,),
        )
        note: dict[str, Any] | None = cursor.fetchone()
        if note is None:
            raise RuntimeError(f"note not found for job: {job_id}")
        return note

    def _update_clip_placeholder(
        self,
        cursor: Any,
        clip_id: UUID,
        values: dict[str, Any],
    ) -> None:
        cursor.execute(
            """
            UPDATE clips
            SET start_sec = %s,
                end_sec = %s,
                title = %s,
                summary_seed = %s,
                summary = %s,
                ai_summary = %s,
                classification = %s,
                confidence = %s,
                status = %s,
                scene_at_sec = %s,
                scene_blob_path = %s,
                scene_caption = %s,
                scene_source = %s,
                needs_regen = true,
                updated_at = now()
            WHERE id = %s
            """,
            (
                values["start_sec"],
                values["end_sec"],
                values["title"],
                values["summary_seed"],
                values["summary"],
                values["ai_summary"],
                values["classification"],
                values["confidence"],
                values["status"],
                values["scene_at_sec"],
                values["scene_blob_path"],
                values["scene_caption"],
                values["scene_source"],
                clip_id,
            ),
        )

    def _complete_clip_mutation(
        self,
        cursor: Any,
        job_id: UUID,
        note: dict[str, Any],
        assemble_markdown: Callable[[list[dict[str, Any]]], str],
    ) -> None:
        if note["is_polished"]:
            cursor.execute(
                """
                UPDATE notes
                SET clips_dirty = true,
                    updated_at = now()
                WHERE job_id = %s
                """,
                (job_id,),
            )
            return
        rows = self._drafted_clip_rows(cursor, job_id)
        cursor.execute(
            """
            UPDATE notes
            SET markdown = %s,
                is_polished = false,
                clips_dirty = false,
                updated_at = now()
            WHERE job_id = %s
            """,
            (assemble_markdown(rows), job_id),
        )

    def drafted_clip_rows(self, job_id: UUID) -> list[dict[str, Any]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                return self._drafted_clip_rows(cursor, job_id)

    def _drafted_clip_rows(self, cursor: Any, job_id: UUID) -> list[dict[str, Any]]:
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
            etag = _etag(row["updated_at"])
            etags.append(etag)
            clips.append(self._clip_view_from_row(row))
        return {"clips": clips, "collection_etag": max(etags) if etags else '""'}

    def _clip_view_from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        scene_blob_path = row["scene_blob_path"]
        return {
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
            "etag": _etag(row["updated_at"]),
        }

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
        snapshot = _clip_snapshot(clips)
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

    def _freeze_version(
        self,
        cursor: Any,
        job_id: UUID,
        kind: str,
        note: dict[str, Any],
    ) -> None:
        clips = self._drafted_clip_rows(cursor, job_id)
        settings = {
            "is_polished": note["is_polished"],
            "include_summary": note["include_summary"],
            "include_transcript": note["include_transcript"],
        }
        cursor.execute(
            "SELECT COALESCE(MAX(seq), 0) + 1 AS seq FROM note_versions WHERE job_id = %s",
            (job_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("version sequence query returned no row")
        seq = row["seq"]
        cursor.execute(
            """
            INSERT INTO note_versions (
                job_id, seq, label, kind, is_baseline,
                note_markdown, note_settings, clips_snapshot
            )
            VALUES (%s, %s, %s, %s, false, %s, %s, %s)
            """,
            (
                job_id,
                seq,
                f"v{seq}",
                kind,
                note["markdown"],
                Jsonb(settings),
                Jsonb(_clip_snapshot(clips)),
            ),
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
