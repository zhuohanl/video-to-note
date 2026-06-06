from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ProxyArtifact:
    blob_path: str
    content: bytes


class FakeAcquirer:
    def download_proxy(self, video_id: UUID) -> ProxyArtifact:
        return ProxyArtifact(blob_path=f"proxy/{video_id}.mp4", content=b"fake-proxy")
