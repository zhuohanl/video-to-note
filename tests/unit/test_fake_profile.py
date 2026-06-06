from pathlib import Path

from vtn_ai.profile import get_profile

EXPECTED_PROFILE_FIELDS = {
    "queue",
    "blob_store",
    "source_resolver",
    "media_acquirer",
    "transcript_provider",
    "frame_sampler",
    "ocr_provider",
    "chat_model",
    "embedding_model",
}


def test_fake_profile_returns_all_offline_adapters() -> None:
    profile = get_profile("fake")

    assert set(profile.adapters()) == EXPECTED_PROFILE_FIELDS
    assert profile.queue.send({"job_id": "job-1"}) == "fake-message-job-1"
    assert profile.blob_store.url_for("frames/job-1/0001.png").startswith("local://")
    assert profile.source_resolver.can_handle("https://www.youtube.com/watch?v=fake")
    assert profile.media_acquirer.download_proxy("video-1") == "local://proxy/video-1.mp4"
    assert profile.transcript_provider.fetch("video-1")[0]["text"] == "Welcome to the session."
    assert profile.frame_sampler.sample("video-1")[0]["event_type"] == "slide"
    assert profile.ocr_provider.extract_text("frame-1") == "Architecture overview"


def test_fake_chat_returns_schema_valid_json_by_kind() -> None:
    profile = get_profile("fake")

    refinement = profile.chat_model.complete_json("kind: refinement", {"required": ["boundaries"]})
    summary = profile.chat_model.complete_json("kind: summary", {"required": ["title", "summary"]})
    style = profile.chat_model.complete_json("kind: style", {"required": ["style_profile"]})

    assert refinement["boundaries"][0]["title"] == "Introduction"
    assert summary["title"] == "Architecture overview"
    assert "worker -> db -> sse -> browser" in summary["summary"]
    assert style["style_profile"]["density"]["source"] == "examples"


def test_fake_embeddings_are_deterministic() -> None:
    profile = get_profile("fake")

    first = profile.embedding_model.embed(["alpha", "beta"])
    second = profile.embedding_model.embed(["alpha", "beta"])

    assert first == second
    assert len(first) == 2
    assert len(first[0]) == 8
    assert first[0] != first[1]


def test_production_packages_do_not_import_tests_or_repo_fixtures() -> None:
    package_root = Path("packages")
    python_files = package_root.glob("vtn_*/src/**/*.py")

    offenders: list[str] = []
    for python_file in python_files:
        text = python_file.read_text(encoding="utf-8")
        if "import tests" in text or "from tests" in text or "import fixtures" in text:
            offenders.append(str(python_file))

    assert offenders == []
