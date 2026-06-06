from __future__ import annotations

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


UPGRADE_SQL = [
    "CREATE EXTENSION IF NOT EXISTS pgcrypto",
    """
    CREATE TABLE videos (
      id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      source_url      text NOT NULL,
      canonical_url   text,
      source_type     text NOT NULL,
      title           text,
      duration_sec    numeric(10,3),
      proxy_blob_path text,
      proxy_state      text NOT NULL DEFAULT 'absent',
      transcript_state text NOT NULL DEFAULT 'absent',
      visual_state     text NOT NULL DEFAULT 'absent',
      proxy_owner_job      uuid,
      transcript_owner_job uuid,
      visual_owner_job     uuid,
      artifacts_updated_at timestamptz NOT NULL DEFAULT now(),
      created_at      timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE UNIQUE INDEX uq_videos_canonical
    ON videos(canonical_url)
    WHERE canonical_url IS NOT NULL
    """,
    """
    CREATE TABLE jobs (
      id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      video_id      uuid NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
      stage         text NOT NULL DEFAULT 'queued'
                      CHECK (stage IN (
                        'queued',
                        'resolving',
                        'acquiring_media',
                        'analyzing',
                        'segmenting',
                        'drafting'
                      )),
      status        text NOT NULL DEFAULT 'active'
                      CHECK (status IN ('active','failed','review_ready','exported','canceled')),
      error_code    text,
      error_message text,
      attempt       int  NOT NULL DEFAULT 0,
      created_at    timestamptz NOT NULL DEFAULT now(),
      updated_at    timestamptz NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX idx_jobs_video ON jobs(video_id)",
    """
    CREATE TABLE prompts (
      job_id        uuid PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
      depth         text NOT NULL,
      custom_prompt text,
      examples      jsonb NOT NULL DEFAULT '[]',
      style_profile jsonb NOT NULL DEFAULT '{}',
      save_style_as_default boolean NOT NULL DEFAULT false,
      model_config  jsonb NOT NULL DEFAULT '{}'
    )
    """,
    """
    CREATE TABLE style_defaults (
      id            boolean PRIMARY KEY DEFAULT true CHECK (id),
      examples      jsonb NOT NULL DEFAULT '[]',
      extracted     jsonb NOT NULL DEFAULT '{}',
      updated_at    timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE transcript_spans (
      id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      video_id    uuid NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
      start_sec   numeric(10,3) NOT NULL,
      end_sec     numeric(10,3) NOT NULL,
      text        text NOT NULL,
      speaker     text,
      source      text NOT NULL
    )
    """,
    "CREATE INDEX idx_spans_video_time ON transcript_spans(video_id, start_sec)",
    "CREATE UNIQUE INDEX uq_spans_video_start ON transcript_spans(video_id, start_sec)",
    """
    CREATE TABLE visual_events (
      id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      video_id    uuid NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
      at_sec      numeric(10,3) NOT NULL,
      event_type  text NOT NULL,
      confidence  real NOT NULL,
      ocr_text    text,
      phash       text,
      frame_blob_path text
    )
    """,
    "CREATE INDEX idx_visual_video_time ON visual_events(video_id, at_sec)",
    "CREATE UNIQUE INDEX uq_visual_video_at_type ON visual_events(video_id, at_sec, event_type)",
    """
    CREATE TABLE clips (
      id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      job_id          uuid NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
      order_index     int  NOT NULL,
      start_sec       numeric(10,3) NOT NULL,
      end_sec         numeric(10,3) NOT NULL,
      title           text,
      summary_seed    text,
      summary         text,
      ai_summary      text,
      classification  text CHECK (classification IN ('text_led','visual_led','mixed')),
      confidence      real,
      status          text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','ready')),
      scene_at_sec    numeric(10,3),
      scene_blob_path text,
      scene_caption   text,
      scene_source    text NOT NULL DEFAULT 'auto' CHECK (scene_source IN ('auto','manual')),
      needs_regen     boolean NOT NULL DEFAULT false,
      updated_at      timestamptz NOT NULL DEFAULT now(),
      UNIQUE (job_id, order_index)
    )
    """,
    "CREATE INDEX idx_clips_job ON clips(job_id, order_index)",
    """
    CREATE TABLE notes (
      job_id             uuid PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
      markdown           text NOT NULL,
      include_summary    boolean NOT NULL DEFAULT true,
      include_transcript boolean NOT NULL DEFAULT false,
      is_polished        boolean NOT NULL DEFAULT false,
      clips_dirty        boolean NOT NULL DEFAULT false,
      CONSTRAINT note_content_nonempty CHECK (include_summary OR include_transcript),
      built_from_version int,
      updated_at         timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE note_versions (
      id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      job_id          uuid NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
      seq             int  NOT NULL,
      label           text NOT NULL,
      kind            text NOT NULL CHECK (kind IN (
                        'initial',
                        'auto_edit',
                        'auto_pre_change',
                        'auto_rebuild',
                        'manual',
                        'restore'
                      )),
      is_baseline     boolean NOT NULL DEFAULT false,
      note_markdown   text NOT NULL,
      note_settings   jsonb NOT NULL DEFAULT '{}',
      clips_snapshot  jsonb NOT NULL,
      created_at      timestamptz NOT NULL DEFAULT now(),
      UNIQUE (job_id, seq)
    )
    """,
    "CREATE INDEX idx_versions_job ON note_versions(job_id, seq DESC)",
    """
    CREATE TABLE job_events (
      id         bigserial PRIMARY KEY,
      job_id     uuid NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
      type       text NOT NULL,
      payload    jsonb NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX idx_events_job ON job_events(job_id, id)",
    """
    CREATE TABLE exports (
      id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      job_id      uuid NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
      zip_blob_path text NOT NULL,
      created_at  timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE job_costs (
      job_id        uuid PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
      estimate_usd  numeric(10,4),
      estimate_json jsonb NOT NULL DEFAULT '{}',
      actual_usd    numeric(10,4),
      actual_json   jsonb NOT NULL DEFAULT '{}',
      computed_at   timestamptz
    )
    """,
]

DOWNGRADE_SQL = [
    "DROP TABLE IF EXISTS job_costs CASCADE",
    "DROP TABLE IF EXISTS exports CASCADE",
    "DROP TABLE IF EXISTS job_events CASCADE",
    "DROP TABLE IF EXISTS note_versions CASCADE",
    "DROP TABLE IF EXISTS notes CASCADE",
    "DROP TABLE IF EXISTS clips CASCADE",
    "DROP TABLE IF EXISTS visual_events CASCADE",
    "DROP TABLE IF EXISTS transcript_spans CASCADE",
    "DROP TABLE IF EXISTS style_defaults CASCADE",
    "DROP TABLE IF EXISTS prompts CASCADE",
    "DROP TABLE IF EXISTS jobs CASCADE",
    "DROP TABLE IF EXISTS videos CASCADE",
]


def upgrade() -> None:
    for statement in UPGRADE_SQL:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_SQL:
        op.execute(statement)
