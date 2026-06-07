from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Protocol
from urllib.parse import parse_qs, urlparse

import yt_dlp  # type: ignore[import-untyped]
from vtn_core.models import SourceType

from vtn_ingest.resolve import ResolvedSource, ResolveError


class MetadataProvider(Protocol):
    def extract(self, url: str) -> dict[str, object]: ...


class StaticMetadataProvider:
    def __init__(self, metadata_by_url: Mapping[str, dict[str, object] | ResolveError]) -> None:
        self.metadata_by_url = metadata_by_url

    def extract(self, url: str) -> dict[str, object]:
        value = self.metadata_by_url.get(url)
        if isinstance(value, ResolveError):
            raise value
        if value is None:
            raise ResolveError("unsupported_url", "No recorded metadata for URL")
        return value


class YtDlpMetadataProvider:
    def extract(self, url: str) -> dict[str, object]:
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as downloader:
                info = downloader.extract_info(url, download=False)
        except Exception as exc:
            raise _map_ytdlp_error(exc) from exc
        if not isinstance(info, dict):
            raise ResolveError("video_unavailable", "yt-dlp returned no metadata")
        return info


class YouTubeResolver:
    def __init__(self, metadata_provider: MetadataProvider | None = None) -> None:
        self.metadata_provider = metadata_provider or YtDlpMetadataProvider()

    def can_handle(self, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return host in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}

    def resolve(self, url: str) -> ResolvedSource:
        metadata = self.metadata_provider.extract(url)
        video_id = str(metadata.get("id") or _youtube_id_from_url(url))
        canonical_url = f"https://www.youtube.com/watch?v={video_id}"
        return _resolved_from_metadata(
            metadata,
            canonical_url=canonical_url,
            source_type=SourceType.youtube,
            media_locator=canonical_url,
        )


class MicrosoftEventResolver:
    def __init__(self, metadata_provider: MetadataProvider | None = None) -> None:
        self.metadata_provider = metadata_provider or YtDlpMetadataProvider()

    def can_handle(self, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        if host not in {"build.microsoft.com", "ignite.microsoft.com"}:
            return False
        return "/sessions/" in urlparse(url).path.lower()

    def resolve(self, url: str) -> ResolvedSource:
        metadata = self.metadata_provider.extract(url)
        canonical_url = str(metadata.get("webpage_url") or url)
        source_type = (
            SourceType.msignite
            if urlparse(canonical_url).netloc.lower() == "ignite.microsoft.com"
            else SourceType.msbuild
        )
        return _resolved_from_metadata(
            metadata,
            canonical_url=canonical_url,
            source_type=source_type,
            media_locator=canonical_url,
        )


class GenericResolver:
    def __init__(self, metadata_provider: MetadataProvider | None = None) -> None:
        self.metadata_provider = metadata_provider or YtDlpMetadataProvider()

    def can_handle(self, url: str) -> bool:
        return urlparse(url).scheme in {"http", "https"}

    def resolve(self, url: str) -> ResolvedSource:
        metadata = self.metadata_provider.extract(url)
        canonical_url = str(metadata.get("webpage_url") or url)
        return _resolved_from_metadata(
            metadata,
            canonical_url=canonical_url,
            source_type=SourceType.other,
            media_locator=canonical_url,
        )


def _resolved_from_metadata(
    metadata: dict[str, object],
    *,
    canonical_url: str,
    source_type: SourceType,
    media_locator: str,
) -> ResolvedSource:
    return ResolvedSource(
        canonical_url=canonical_url,
        source_type=source_type,
        title=str(metadata.get("title") or "Untitled video"),
        duration_sec=_duration(metadata.get("duration")),
        caption_tracks=_caption_tracks(metadata),
        media_locator=media_locator,
    )


def _duration(value: object) -> Decimal:
    if value is None:
        return Decimal("0.000")
    return Decimal(str(value)).quantize(Decimal("0.001"))


def _caption_tracks(metadata: dict[str, object]) -> list[dict[str, object]]:
    tracks: list[dict[str, object]] = []
    for key in ("subtitles", "automatic_captions"):
        raw_tracks = metadata.get(key)
        if not isinstance(raw_tracks, dict):
            continue
        for language, entries in raw_tracks.items():
            ext = None
            if isinstance(entries, list) and entries:
                first = entries[0]
                if isinstance(first, dict):
                    ext = first.get("ext")
            tracks.append(
                {
                    "kind": key,
                    "language": str(language),
                    "ext": ext,
                }
            )
    return tracks


def _youtube_id_from_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc.lower() == "youtu.be":
        return parsed.path.strip("/")
    query_id = parse_qs(parsed.query).get("v", [""])[0]
    if not query_id:
        raise ResolveError("unsupported_url", "YouTube URL is missing a video id")
    return query_id


def _map_ytdlp_error(exc: Exception) -> ResolveError:
    message = str(exc)
    lowered = message.lower()
    if "unsupported url" in lowered or "no suitable extractor" in lowered:
        return ResolveError("unsupported_url", message)
    if any(token in lowered for token in ("unavailable", "private", "age", "sign in")):
        return ResolveError("video_unavailable", message)
    return ResolveError("video_unavailable", message)
