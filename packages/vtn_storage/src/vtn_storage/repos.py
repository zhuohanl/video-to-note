from __future__ import annotations

from typing import Any, cast
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from vtn_core.models import Job, SourceType


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
