from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import psycopg
import pytest
from vtn_core.models import SourceType, TranscriptSource
from vtn_ingest.acquire import FakeAcquirer, ProxyArtifact
from vtn_storage.repos import JobRepository
from vtn_transcript.chain import FakeTranscriptProvider, TranscriptResult, TranscriptSpanData
from vtn_visual.index import FakeFrameSampler, VisualEventData
from vtn_worker.runner import StageContext
from vtn_worker.stages.acquiring_media import acquire_media
from vtn_worker.stages.index_visual import index_visual
from vtn_worker.stages.transcribe import transcribe


def _database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", "postgresql://vtn:vtn@127.0.0.1:55432/vtn")


def _alembic(*args: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = _database_url()
    subprocess.run(["alembic", *args], check=True, env=env, capture_output=True, text=True)


def _shared_jobs(repo: JobRepository) -> tuple[UUID, UUID, UUID]:
    video_id = repo.create_video("https://example.test/shared", SourceType.youtube)
    return video_id, repo.create_job(video_id), repo.create_job(video_id)


@dataclass
class CountingAcquirer(FakeAcquirer):
    calls: int = 0

    def download_proxy(self, video_id: UUID) -> ProxyArtifact:
        self.calls += 1
        return ProxyArtifact(blob_path=f"proxy/{video_id}.mp4", content=b"fake")


@dataclass
class CountingTranscriptProvider(FakeTranscriptProvider):
    calls: int = 0

    def fetch(self, video_id: UUID) -> TranscriptResult:
        self.calls += 1
        return TranscriptResult(
            source=TranscriptSource.youtube_captions,
            spans=[
                TranscriptSpanData(
                    Decimal("0.000"),
                    Decimal("2.000"),
                    f"Transcript for {video_id}",
                    None,
                )
            ],
        )


@dataclass
class CountingFrameSampler(FakeFrameSampler):
    calls: int = 0

    def sample(self, video_id: UUID) -> list[VisualEventData]:
        self.calls += 1
        return super().sample(video_id)


@pytest.mark.asyncio
async def test_shared_video_artifact_cas_allows_one_builder_per_artifact() -> None:
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    repo = JobRepository(_database_url())
    video_id, first_job, second_job = _shared_jobs(repo)
    acquirer = CountingAcquirer()
    transcript_provider = CountingTranscriptProvider()
    frame_sampler = CountingFrameSampler()

    await acquire_media(
        StageContext(first_job, 0, "acquiring_media", repo),
        acquirer=acquirer,
    )
    await acquire_media(
        StageContext(second_job, 0, "acquiring_media", repo),
        acquirer=acquirer,
    )
    await transcribe(
        StageContext(first_job, 0, "transcribe", repo),
        provider=transcript_provider,
    )
    await transcribe(
        StageContext(second_job, 0, "transcribe", repo),
        provider=transcript_provider,
    )
    await index_visual(
        StageContext(first_job, 0, "index visual", repo),
        sampler=frame_sampler,
    )
    await index_visual(
        StageContext(second_job, 0, "index visual", repo),
        sampler=frame_sampler,
    )

    assert acquirer.calls == 1
    assert transcript_provider.calls == 1
    assert frame_sampler.calls == 1
    assert repo.proxy_blob_path(video_id) == f"proxy/{video_id}.mp4"
    assert len(repo.transcript_span_rows(video_id)) == 1
    assert len(repo.visual_event_rows(video_id)) == 6


def test_stale_building_artifact_can_be_reclaimed_without_duplicate_rows() -> None:
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    repo = JobRepository(_database_url())
    video_id, winner_job, takeover_job = _shared_jobs(repo)

    assert repo.claim_artifact(video_id, winner_job, "proxy")
    repo.release_on_fail(video_id, winner_job, "proxy")
    assert repo.artifact_state(video_id, "proxy") == "absent"
    assert repo.claim_artifact(video_id, takeover_job, "proxy")

    assert repo.claim_artifact(video_id, winner_job, "transcript")
    with psycopg.connect(_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO transcript_spans (video_id, start_sec, end_sec, text, speaker, source)
                VALUES (%s, 0.000, 2.000, 'partial', NULL, %s)
                """,
                (video_id, TranscriptSource.youtube_captions.value),
            )
            cursor.execute(
                """
                UPDATE videos
                SET artifacts_updated_at = now() - interval '2 hours'
                WHERE id = %s
                """,
                (video_id,),
            )

    assert repo.reclaim_stale(
        video_id,
        takeover_job,
        "transcript",
        stale_after=timedelta(minutes=15),
    )
    repo.replace_transcript_spans(
        video_id,
        [
            {
                "start_sec": Decimal("0.000"),
                "end_sec": Decimal("3.000"),
                "text": "recovered",
                "speaker": None,
            }
        ],
        TranscriptSource.azure_speech,
    )

    rows = repo.transcript_span_rows(video_id)
    assert len(rows) == 1
    assert rows[0]["text"] == "recovered"
    assert rows[0]["source"] == TranscriptSource.azure_speech.value
