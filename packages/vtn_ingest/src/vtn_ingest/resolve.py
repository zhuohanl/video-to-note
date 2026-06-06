from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol

from vtn_core.models import SourceType


@dataclass(frozen=True)
class ResolvedSource:
    canonical_url: str
    source_type: SourceType
    title: str
    duration_sec: Decimal
    caption_tracks: list[dict[str, object]] = field(default_factory=list)
    media_locator: str | None = None


class ResolveError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class SourceResolver(Protocol):
    def can_handle(self, url: str) -> bool: ...

    def resolve(self, url: str) -> ResolvedSource: ...


class ResolverRegistry:
    def __init__(self, resolvers: list[SourceResolver]) -> None:
        self.resolvers = resolvers

    def resolve(self, url: str) -> ResolvedSource:
        for resolver in self.resolvers:
            if resolver.can_handle(url):
                return resolver.resolve(url)
        raise ResolveError("unsupported_url", "Unsupported URL")


class FakeResolver:
    def can_handle(self, url: str) -> bool:
        return url.startswith(("https://www.youtube.com/", "https://youtube.com/"))

    def resolve(self, url: str) -> ResolvedSource:
        if "unavailable" in url:
            raise ResolveError("video_unavailable", "Video is unavailable")
        return ResolvedSource(
            canonical_url="https://www.youtube.com/watch?v=fake",
            source_type=SourceType.youtube,
            title="Fake conference session",
            duration_sec=Decimal("30.000"),
            caption_tracks=[{"kind": "captions", "language": "en"}],
            media_locator=url,
        )
