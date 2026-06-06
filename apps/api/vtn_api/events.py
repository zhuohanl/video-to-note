from __future__ import annotations

import json
from typing import Any, ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EventModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: ClassVar[str]

    def payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class StageEvent(EventModel):
    type: ClassVar[str] = "stage"
    stage: str


class CostEstimateEvent(EventModel):
    type: ClassVar[str] = "cost.estimate"
    usd: float
    breakdown: dict[str, Any]


class StyleResolvedEvent(EventModel):
    type: ClassVar[str] = "style.resolved"
    profile: dict[str, Any]


class ClipReadyEvent(EventModel):
    type: ClassVar[str] = "clip.ready"
    clip_id: str
    order_index: int


class WarningEvent(EventModel):
    type: ClassVar[str] = "warning"
    code: str
    message: str


class ErrorEvent(EventModel):
    type: ClassVar[str] = "error"
    code: str
    message: str
    stage: str


class DoneEvent(EventModel):
    type: ClassVar[str] = "done"


class JobEventRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    job_id: UUID
    type: str
    payload: dict[str, Any]


def to_sse(row: JobEventRow) -> str:
    data = json.dumps(row.payload, separators=(",", ":"))
    return f"id: {row.id}\nevent: {row.type}\ndata: {data}\n\n"
