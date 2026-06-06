import os
import subprocess

import psycopg

APP_TABLES = {
    "videos",
    "jobs",
    "prompts",
    "style_defaults",
    "transcript_spans",
    "visual_events",
    "clips",
    "notes",
    "note_versions",
    "job_events",
    "exports",
    "job_costs",
}


def _database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", "postgresql://vtn:vtn@127.0.0.1:55432/vtn")


def _alembic(*args: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = _database_url()
    subprocess.run(["alembic", *args], check=True, env=env, capture_output=True, text=True)


def _fetch_set(sql: str) -> set[str]:
    with psycopg.connect(_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return {row[0] for row in cursor.fetchall()}


def test_initial_migration_upgrade_and_downgrade() -> None:
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")

    tables = _fetch_set(
        """
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        """
    )
    assert APP_TABLES <= tables

    indexes = _fetch_set(
        """
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname = 'public'
        """
    )
    assert {
        "uq_videos_canonical",
        "idx_jobs_video",
        "idx_spans_video_time",
        "uq_spans_video_start",
        "idx_visual_video_time",
        "uq_visual_video_at_type",
        "idx_clips_job",
        "idx_versions_job",
        "idx_events_job",
    } <= indexes

    constraints = _fetch_set(
        """
        SELECT conname
        FROM pg_constraint
        WHERE connamespace = 'public'::regnamespace
        """
    )
    assert {
        "clips_job_id_order_index_key",
        "note_versions_job_id_seq_key",
        "style_defaults_id_check",
        "note_content_nonempty",
    } <= constraints

    columns = _fetch_set(
        """
        SELECT table_name || '.' || column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
        """
    )
    assert {
        "videos.canonical_url",
        "jobs.stage",
        "prompts.model_config",
        "clips.scene_caption",
        "notes.include_summary",
        "note_versions.clips_snapshot",
        "job_costs.actual_json",
    } <= columns

    _alembic("downgrade", "base")
    remaining = _fetch_set(
        """
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        """
    )
    assert APP_TABLES.isdisjoint(remaining)
