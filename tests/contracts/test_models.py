from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from vtn_core import models
from vtn_core.state_machine import legal_status, legal_transition


def _now() -> datetime:
    return datetime.now(tz=UTC)


def test_enums_match_spec_literals_exactly() -> None:
    assert [item.value for item in models.JobStage] == [
        "queued",
        "resolving",
        "acquiring_media",
        "analyzing",
        "segmenting",
        "drafting",
    ]
    assert [item.value for item in models.JobStatus] == [
        "active",
        "review_ready",
        "exported",
        "failed",
        "canceled",
    ]
    assert [item.value for item in models.ArtifactState] == ["absent", "building", "ready"]
    assert [item.value for item in models.ClipStatus] == ["pending", "ready"]
    assert [item.value for item in models.Classification] == ["text_led", "visual_led", "mixed"]
    assert [item.value for item in models.SceneSource] == ["auto", "manual"]
    assert [item.value for item in models.VersionKind] == [
        "initial",
        "auto_edit",
        "auto_pre_change",
        "auto_rebuild",
        "manual",
        "restore",
    ]
    assert [item.value for item in models.TranscriptSource] == [
        "source_captions",
        "youtube_captions",
        "azure_speech",
    ]
    assert [item.value for item in models.SourceType] == [
        "youtube",
        "msbuild",
        "msignite",
        "other",
    ]


@pytest.mark.parametrize(
    "model_instance",
    [
        models.Video(
            id=uuid4(),
            source_url="https://youtu.be/demo",
            canonical_url="https://www.youtube.com/watch?v=demo",
            source_type=models.SourceType.youtube,
            title="Demo",
            duration_sec=Decimal("30.000"),
            proxy_blob_path="proxy/demo.mp4",
            proxy_state=models.ArtifactState.ready,
            transcript_state=models.ArtifactState.ready,
            visual_state=models.ArtifactState.absent,
            proxy_owner_job=uuid4(),
            transcript_owner_job=None,
            visual_owner_job=None,
            artifacts_updated_at=_now(),
            created_at=_now(),
        ),
        models.Job(id=uuid4(), video_id=uuid4(), created_at=_now(), updated_at=_now()),
        models.Prompt(job_id=uuid4(), depth=models.PromptDepth.balanced),
        models.StyleDefault(updated_at=_now()),
        models.TranscriptSpan(
            id=uuid4(),
            video_id=uuid4(),
            start_sec=Decimal("0.000"),
            end_sec=Decimal("4.200"),
            text="hello",
            speaker="Speaker 1",
            source=models.TranscriptSource.youtube_captions,
        ),
        models.VisualEvent(
            id=uuid4(),
            video_id=uuid4(),
            at_sec=Decimal("1.000"),
            event_type="slide_change",
            confidence=0.9,
            ocr_text="Title",
            phash="8f1c",
            frame_blob_path="frames/1.png",
        ),
        models.Clip(
            id=uuid4(),
            job_id=uuid4(),
            order_index=0,
            start_sec=Decimal("0.000"),
            end_sec=Decimal("10.000"),
            title="Intro",
            classification=models.Classification.mixed,
            status=models.ClipStatus.ready,
            scene_source=models.SceneSource.auto,
            updated_at=_now(),
        ),
        models.Note(job_id=uuid4(), markdown="# Note", updated_at=_now()),
        models.NoteVersion(
            id=uuid4(),
            job_id=uuid4(),
            seq=1,
            label="v1",
            kind=models.VersionKind.initial,
            is_baseline=True,
            note_markdown="# Note",
            clips_snapshot=[],
            created_at=_now(),
        ),
        models.JobEvent(
            id=1,
            job_id=uuid4(),
            type="stage",
            payload={"stage": "queued"},
            created_at=_now(),
        ),
        models.Export(
            id=uuid4(),
            job_id=uuid4(),
            zip_blob_path="exports/job.zip",
            created_at=_now(),
        ),
        models.JobCost(job_id=uuid4(), estimate_usd=Decimal("0.1000"), computed_at=_now()),
    ],
)
def test_models_round_trip_to_and_from_dict(model_instance: models.DomainModel) -> None:
    dumped = model_instance.model_dump(mode="json")
    restored = type(model_instance).model_validate(dumped)

    assert restored == model_instance


def test_note_requires_at_least_one_content_flag() -> None:
    with pytest.raises(ValidationError):
        models.Note(
            job_id=uuid4(),
            markdown="# Note",
            include_summary=False,
            include_transcript=False,
            updated_at=_now(),
        )


def test_state_machine_allows_only_spec_transitions() -> None:
    assert legal_transition(models.JobStage.queued, models.JobStage.resolving)
    assert legal_transition(models.JobStage.resolving, models.JobStage.acquiring_media)
    assert legal_transition(models.JobStage.acquiring_media, models.JobStage.analyzing)
    assert legal_transition(models.JobStage.analyzing, models.JobStage.segmenting)
    assert legal_transition(models.JobStage.segmenting, models.JobStage.drafting)

    with pytest.raises(ValueError):
        legal_transition(models.JobStage.drafting, models.JobStage.resolving)

    assert legal_status(models.JobStatus.active, models.JobStatus.review_ready)
    assert legal_status(models.JobStatus.review_ready, models.JobStatus.exported)
    assert legal_status(models.JobStatus.active, models.JobStatus.failed)
    assert legal_status(models.JobStatus.active, models.JobStatus.canceled)

    illegal_status_transitions = [
        (models.JobStatus.review_ready, models.JobStatus.failed),
        (models.JobStatus.review_ready, models.JobStatus.canceled),
        (models.JobStatus.exported, models.JobStatus.active),
        (models.JobStatus.exported, models.JobStatus.failed),
        (models.JobStatus.exported, models.JobStatus.canceled),
    ]
    for from_status, to_status in illegal_status_transitions:
        with pytest.raises(ValueError):
            legal_status(from_status, to_status)


def test_uuid_fields_accept_uuid_instances() -> None:
    video_id = uuid4()
    job = models.Job(id=uuid4(), video_id=video_id, created_at=_now(), updated_at=_now())

    assert isinstance(job.video_id, UUID)
