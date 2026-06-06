from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
from vtn_core.models import SourceType
from vtn_ingest.resolve import ResolveError, ResolverRegistry
from vtn_ingest.resolvers import (
    GenericResolver,
    MicrosoftEventResolver,
    StaticMetadataProvider,
    YouTubeResolver,
)

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "ingest"


def _metadata(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / name).read_text())


def test_real_resolvers_resolve_recorded_metadata_without_network() -> None:
    provider = StaticMetadataProvider(
        {
            "https://youtu.be/jNQXAC9IVRw": _metadata("youtube_metadata.json"),
            "https://build.microsoft.com/en-US/sessions/build-session-demo": _metadata(
                "msbuild_metadata.json"
            ),
            "https://example.com/videos/generic-session": _metadata("generic_metadata.json"),
        }
    )
    registry = ResolverRegistry(
        [
            YouTubeResolver(provider),
            MicrosoftEventResolver(provider),
            GenericResolver(provider),
        ]
    )

    youtube = registry.resolve("https://youtu.be/jNQXAC9IVRw")
    assert youtube.canonical_url == "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    assert youtube.source_type == SourceType.youtube
    assert youtube.title == "Me at the zoo"
    assert youtube.duration_sec == Decimal("19.000")
    assert youtube.caption_tracks == [{"kind": "subtitles", "language": "en", "ext": "vtt"}]
    assert youtube.media_locator == "https://www.youtube.com/watch?v=jNQXAC9IVRw"

    build = registry.resolve("https://build.microsoft.com/en-US/sessions/build-session-demo")
    assert build.canonical_url == "https://build.microsoft.com/en-US/sessions/build-session-demo"
    assert build.source_type == SourceType.msbuild
    assert build.title == "Build session demo"
    assert build.duration_sec == Decimal("1800.000")

    generic = registry.resolve("https://example.com/videos/generic-session")
    assert generic.canonical_url == "https://example.com/videos/generic-session"
    assert generic.source_type == SourceType.other
    assert generic.title == "Generic conference video"
    assert generic.duration_sec == Decimal("900.000")


def test_real_resolvers_map_provider_failures_to_contract_errors() -> None:
    provider = StaticMetadataProvider(
        {
            "https://www.youtube.com/watch?v=private": ResolveError(
                "video_unavailable",
                "Private video",
            ),
            "https://ftp.example.com/video": ResolveError("unsupported_url", "Unsupported URL"),
        }
    )

    with pytest.raises(ResolveError) as unavailable:
        YouTubeResolver(provider).resolve("https://www.youtube.com/watch?v=private")
    assert unavailable.value.code == "video_unavailable"

    with pytest.raises(ResolveError) as unsupported:
        GenericResolver(provider).resolve("https://ftp.example.com/video")
    assert unsupported.value.code == "unsupported_url"
