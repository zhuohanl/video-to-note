from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class JobStage(StrEnum):
    queued = "queued"
    resolving = "resolving"
    acquiring_media = "acquiring_media"
    analyzing = "analyzing"
    segmenting = "segmenting"
    drafting = "drafting"


class JobStatus(StrEnum):
    active = "active"
    review_ready = "review_ready"
    exported = "exported"
    failed = "failed"
    canceled = "canceled"


class ArtifactState(StrEnum):
    absent = "absent"
    building = "building"
    ready = "ready"


class ClipStatus(StrEnum):
    pending = "pending"
    ready = "ready"


class Classification(StrEnum):
    text_led = "text_led"
    visual_led = "visual_led"
    mixed = "mixed"


class SceneSource(StrEnum):
    auto = "auto"
    manual = "manual"


class VersionKind(StrEnum):
    initial = "initial"
    auto_edit = "auto_edit"
    auto_pre_change = "auto_pre_change"
    auto_rebuild = "auto_rebuild"
    manual = "manual"
    restore = "restore"


class TranscriptSource(StrEnum):
    source_captions = "source_captions"
    youtube_captions = "youtube_captions"
    azure_speech = "azure_speech"


class SourceType(StrEnum):
    youtube = "youtube"
    msbuild = "msbuild"
    msignite = "msignite"
    other = "other"


class PromptDepth(StrEnum):
    thorough = "thorough"
    balanced = "balanced"
    brief = "brief"
    custom = "custom"


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Video(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    source_url: str
    canonical_url: str | None = None
    source_type: SourceType
    title: str | None = None
    duration_sec: Decimal | None = None
    proxy_blob_path: str | None = None
    proxy_state: ArtifactState = ArtifactState.absent
    transcript_state: ArtifactState = ArtifactState.absent
    visual_state: ArtifactState = ArtifactState.absent
    proxy_owner_job: UUID | None = None
    transcript_owner_job: UUID | None = None
    visual_owner_job: UUID | None = None
    artifacts_updated_at: datetime
    created_at: datetime


class Job(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    video_id: UUID
    stage: JobStage = JobStage.queued
    status: JobStatus = JobStatus.active
    error_code: str | None = None
    error_message: str | None = None
    attempt: int = 0
    created_at: datetime
    updated_at: datetime


class Prompt(DomainModel):
    job_id: UUID
    depth: PromptDepth
    custom_prompt: str | None = None
    examples: list[dict[str, Any]] = Field(default_factory=list)
    style_profile: dict[str, Any] = Field(default_factory=dict)
    save_style_as_default: bool = False
    model_config_json: dict[str, Any] = Field(default_factory=dict, alias="model_config")


class StyleDefault(DomainModel):
    id: bool = True
    examples: list[dict[str, Any]] = Field(default_factory=list)
    extracted: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime


class TranscriptSpan(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    video_id: UUID
    start_sec: Decimal
    end_sec: Decimal
    text: str
    speaker: str | None = None
    source: TranscriptSource


class VisualEvent(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    video_id: UUID
    at_sec: Decimal
    event_type: str
    confidence: float
    ocr_text: str | None = None
    phash: str | None = None
    frame_blob_path: str | None = None


class Clip(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    order_index: int
    start_sec: Decimal
    end_sec: Decimal
    title: str | None = None
    summary_seed: str | None = None
    summary: str | None = None
    ai_summary: str | None = None
    classification: Classification | None = None
    confidence: float | None = None
    status: ClipStatus = ClipStatus.pending
    scene_at_sec: Decimal | None = None
    scene_blob_path: str | None = None
    scene_caption: str | None = None
    scene_source: SceneSource = SceneSource.auto
    needs_regen: bool = False
    updated_at: datetime


class Note(DomainModel):
    job_id: UUID
    markdown: str
    include_summary: bool = True
    include_transcript: bool = False
    is_polished: bool = False
    clips_dirty: bool = False
    built_from_version: int | None = None
    updated_at: datetime

    @model_validator(mode="after")
    def content_is_not_empty(self) -> Note:
        if not self.include_summary and not self.include_transcript:
            msg = "include_summary or include_transcript must be true"
            raise ValueError(msg)
        return self


class NoteVersion(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    seq: int
    label: str
    kind: VersionKind
    is_baseline: bool = False
    note_markdown: str
    note_settings: dict[str, Any] = Field(default_factory=dict)
    clips_snapshot: list[dict[str, Any]]
    created_at: datetime


class JobEvent(DomainModel):
    id: int
    job_id: UUID
    type: str
    payload: dict[str, Any]
    created_at: datetime


class Export(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    zip_blob_path: str
    created_at: datetime


class JobCost(DomainModel):
    job_id: UUID
    estimate_usd: Decimal | None = None
    estimate_json: dict[str, Any] = Field(default_factory=dict)
    actual_usd: Decimal | None = None
    actual_json: dict[str, Any] = Field(default_factory=dict)
    computed_at: datetime | None = None
