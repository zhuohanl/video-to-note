from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from vtn_core.models import ClipStatus, JobStage, JobStatus, PromptDepth, SceneSource


class ApiSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginBody(ApiSchema):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class CreateJob(ApiSchema):
    url: str
    depth: PromptDepth
    custom_prompt: str | None = None
    examples: list[dict[str, Any]] = Field(default_factory=list)
    use_saved_style: bool = False

    @field_validator("url")
    @classmethod
    def url_must_be_http(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            msg = "url must be http or https"
            raise ValueError(msg)
        return value


class JobView(ApiSchema):
    id: UUID
    status: JobStatus
    stage: JobStage
    error_code: str | None = None
    error_message: str | None = None
    cost: dict[str, Any] = Field(default_factory=dict)


class ClipView(ApiSchema):
    id: UUID
    order_index: int
    start_sec: Decimal
    end_sec: Decimal
    title: str | None = None
    summary: str | None = None
    scene_caption: str | None = None
    status: ClipStatus
    scene_at_sec: Decimal | None = None
    scene_url: str | None = None
    scene_source: SceneSource
    needs_regen: bool = False
    etag: str


class ClipsView(ApiSchema):
    clips: list[ClipView]
    collection_etag: str


class NoteView(ApiSchema):
    markdown: str
    include_summary: bool = True
    include_transcript: bool = False
    is_polished: bool = False
    clips_dirty: bool = False
    etag: str

    @model_validator(mode="after")
    def content_is_not_empty(self) -> NoteView:
        if not self.include_summary and not self.include_transcript:
            msg = "include_summary or include_transcript must be true"
            raise ValueError(msg)
        return self


class PatchClip(ApiSchema):
    title: str | None = None
    summary: str | None = None
    scene_caption: str | None = None


class SplitBody(ApiSchema):
    at_sec: Decimal = Field(ge=0)


class MergeBody(ApiSchema):
    clip_ids: list[UUID] = Field(min_length=1)


class PutNote(ApiSchema):
    markdown: str


class PatchNote(ApiSchema):
    include_summary: bool | None = None
    include_transcript: bool | None = None

    @model_validator(mode="after")
    def content_patch_is_not_empty_when_both_set(self) -> PatchNote:
        if self.include_summary is False and self.include_transcript is False:
            msg = "include_summary or include_transcript must remain true"
            raise ValueError(msg)
        return self


class VersionView(ApiSchema):
    seq: int
    label: str
    kind: str
    created_at: datetime | None = None
    baseline: bool = False


class CreateVersion(ApiSchema):
    label: str | None = None


class ExportView(ApiSchema):
    download_url: str
