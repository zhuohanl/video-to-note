from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

import yt_dlp  # type: ignore[import-untyped]
from vtn_storage.blob import BlobStore

from vtn_ingest.acquire import ProxyArtifact
from vtn_ingest.resolvers import _map_ytdlp_error

FORMAT_SELECTOR = "bv*[height<=720]+ba/b[height<=720]/b"


class Downloader(Protocol):
    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    def extract_info(self, url: str, *, download: bool) -> dict[str, object]: ...


DownloaderFactory = Callable[[dict[str, object]], Downloader]


class YtDlpAcquirer:
    def __init__(
        self,
        *,
        blob_store: BlobStore,
        media_locator: str,
        downloader_factory: DownloaderFactory | None = None,
        work_dir: Path | None = None,
        ffmpeg_location: str | None = None,
    ) -> None:
        self.blob_store = blob_store
        self.media_locator = media_locator
        self.downloader_factory = downloader_factory or yt_dlp.YoutubeDL
        self.work_dir = work_dir
        self.ffmpeg_location = ffmpeg_location

    def download_proxy(self, video_id: UUID) -> ProxyArtifact:
        if self.work_dir is None:
            with TemporaryDirectory() as temp_dir:
                return self._download(video_id, Path(temp_dir))
        self.work_dir.mkdir(parents=True, exist_ok=True)
        return self._download(video_id, self.work_dir)

    def _download(self, video_id: UUID, work_dir: Path) -> ProxyArtifact:
        output_template = str(work_dir / f"{video_id}.%(ext)s")
        options: dict[str, object] = {
            "format": FORMAT_SELECTOR,
            "outtmpl": output_template,
            "download_sections": ["*0-30"],
            "force_keyframes_at_cuts": True,
            "quiet": True,
            "noprogress": True,
        }
        if self.ffmpeg_location:
            options["ffmpeg_location"] = self.ffmpeg_location

        try:
            with self.downloader_factory(options) as downloader:
                info = downloader.extract_info(self.media_locator, download=True)
        except Exception as exc:
            raise _map_ytdlp_error(exc) from exc

        path = self._downloaded_path(info, work_dir, video_id)
        content = path.read_bytes()
        blob_path = f"proxy/{video_id}.mp4"
        self.blob_store.put(blob_path, content)
        return ProxyArtifact(blob_path=blob_path, content=content)

    def _downloaded_path(self, info: object, work_dir: Path, video_id: UUID) -> Path:
        if isinstance(info, dict):
            requested = info.get("requested_downloads")
            if isinstance(requested, list) and requested:
                first = requested[0]
                if isinstance(first, dict) and first.get("filepath"):
                    return Path(str(first["filepath"]))

        matches = sorted(work_dir.glob(f"{video_id}.*"))
        if not matches:
            raise FileNotFoundError(f"yt-dlp did not produce a proxy for {video_id}")
        return matches[0]
