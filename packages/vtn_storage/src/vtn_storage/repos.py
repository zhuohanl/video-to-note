from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from vtn_core.models import Job, JobStage, JobStatus, PromptDepth, SourceType


@dataclass(frozen=True)
class JobSubmission:
    job_id: UUID
    cost_estimate: dict[str, Any]


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
