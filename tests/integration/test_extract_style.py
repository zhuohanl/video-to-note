from __future__ import annotations

import os
import subprocess
from uuid import UUID

import pytest
from vtn_core.invariants import assert_style_profile_valid
from vtn_core.models import PromptDepth
from vtn_storage.repos import JobRepository
from vtn_worker.runner import StageContext
from vtn_worker.stages.extract_style import extract_style


def _database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", "postgresql://vtn:vtn@127.0.0.1:55432/vtn")


def _alembic(*args: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = _database_url()
    subprocess.run(["alembic", *args], check=True, env=env, capture_output=True, text=True)


def _create_job(repo: JobRepository, examples: list[dict[str, object]]) -> UUID:
    return repo.create_submission(
        url="https://www.youtube.com/watch?v=demo",
        depth=PromptDepth.balanced,
        custom_prompt=None,
        examples=examples,
        use_saved_style=False,
    ).job_id


class StyleChat:
    def complete_json(self, prompt: str, schema: dict[str, object] | None = None):
        del prompt, schema
        return {
            "style_descriptor": "Practical sections",
            "granularity": {"value": "fine", "confidence": 0.9},
            "density": {"value": "high", "confidence": 0.9},
            "derived_prompt": "Write sectioned notes",
        }


class FailingStyleChat:
    def complete_json(self, prompt: str, schema: dict[str, object] | None = None):
        del prompt, schema
        return {"invalid": True}


@pytest.mark.asyncio
async def test_extract_style_populates_profile_and_emits_event() -> None:
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    repo = JobRepository(_database_url())
    job_id = _create_job(repo, [{"name": "example.md", "markdown": "# Example"}])

    await extract_style(
        StageContext(job_id, 0, "extract style", repo),
        chat_model=StyleChat(),
    )

    profile = repo.get_prompt(job_id)["style_profile"]
    assert_style_profile_valid(profile)
    assert profile["granularity"]["source"] == "examples"
    events = repo.list_events_after(job_id, 0)
    assert events[-1]["type"] == "style.resolved"
    assert events[-1]["payload"]["profile"] == profile


@pytest.mark.asyncio
async def test_extract_style_falls_back_to_depth_with_warning_on_invalid_llm() -> None:
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    repo = JobRepository(_database_url())
    job_id = _create_job(repo, [{"name": "thin.md", "markdown": "tiny"}])

    await extract_style(
        StageContext(job_id, 0, "extract style", repo),
        chat_model=FailingStyleChat(),
    )

    profile = repo.get_prompt(job_id)["style_profile"]
    assert profile["granularity"] == {"value": "medium", "confidence": 1.0, "source": "depth"}
    event_types = [event["type"] for event in repo.list_events_after(job_id, 0)]
    assert "warning" in event_types
    assert event_types[-1] == "style.resolved"
