import json
from uuid import uuid4

import pytest
from vtn_api.events import (
    ClipReadyEvent,
    CostEstimateEvent,
    DoneEvent,
    ErrorEvent,
    JobEventRow,
    StageEvent,
    StyleResolvedEvent,
    WarningEvent,
    to_sse,
)


@pytest.mark.parametrize(
    "event",
    [
        StageEvent(stage="resolving"),
        CostEstimateEvent(usd=0.12, breakdown={"llm": 0.1, "ocr": 0.02}),
        StyleResolvedEvent(profile={"density": {"value": "medium", "source": "depth"}}),
        ClipReadyEvent(clip_id=str(uuid4()), order_index=0),
        WarningEvent(code="asr_fallback", message="Using ASR fallback"),
        ErrorEvent(code="transcript_failed", message="No transcript", stage="analyzing"),
        DoneEvent(),
    ],
)
def test_event_models_have_spec_type_and_payload(event: object) -> None:
    payload = event.payload()  # type: ignore[attr-defined]

    assert event.type  # type: ignore[attr-defined]
    assert isinstance(payload, dict)


def test_to_sse_renders_replayable_frame() -> None:
    row = JobEventRow(
        id=42,
        job_id=uuid4(),
        type="clip.ready",
        payload={"clip_id": str(uuid4()), "order_index": 3},
    )

    frame = to_sse(row)
    lines = frame.splitlines()

    assert lines[0] == "id: 42"
    assert lines[1] == "event: clip.ready"
    assert lines[2].startswith("data: ")
    assert json.loads(lines[2].removeprefix("data: ")) == row.payload
    assert frame.endswith("\n\n")


def test_all_c3_event_types_are_covered() -> None:
    assert {
        StageEvent.type,
        CostEstimateEvent.type,
        StyleResolvedEvent.type,
        ClipReadyEvent.type,
        WarningEvent.type,
        ErrorEvent.type,
        DoneEvent.type,
    } == {
        "stage",
        "cost.estimate",
        "style.resolved",
        "clip.ready",
        "warning",
        "error",
        "done",
    }
