from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from vtn_ingest.resolve import ResolveError
from vtn_ingest.ytdlp_acquirer import FORMAT_SELECTOR, YtDlpAcquirer
from vtn_storage.blob import LocalBlobStore


class FakeDownloader:
    calls: list[dict[str, object]] = []

    def __init__(self, options: dict[str, object]) -> None:
        self.options = options

    def __enter__(self) -> FakeDownloader:
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def extract_info(self, url: str, *, download: bool) -> dict[str, object]:
        self.calls.append({"url": url, "download": download, "options": self.options})
        output_template = str(self.options["outtmpl"])
        path = Path(output_template.replace("%(ext)s", "mp4"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"proxy-bytes")
        return {"requested_downloads": [{"filepath": str(path)}]}


def test_ytdlp_acquirer_downloads_30s_720p_proxy_to_blob(tmp_path) -> None:
    FakeDownloader.calls = []
    blob_store = LocalBlobStore(tmp_path / "blob")
    acquirer = YtDlpAcquirer(
        blob_store=blob_store,
        media_locator="https://www.youtube.com/watch?v=jNQXAC9IVRw",
        downloader_factory=FakeDownloader,
        work_dir=tmp_path / "work",
        ffmpeg_location="C:/ffmpeg/bin",
    )
    video_id = uuid4()

    artifact = acquirer.download_proxy(video_id)

    assert artifact.blob_path == f"proxy/{video_id}.mp4"
    assert blob_store.get(artifact.blob_path) == b"proxy-bytes"
    call = FakeDownloader.calls[0]
    assert call["url"] == "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    assert call["download"] is True
    options = call["options"]
    assert options["format"] == FORMAT_SELECTOR
    assert options["download_sections"] == ["*0-30"]
    assert options["force_keyframes_at_cuts"] is True
    assert options["ffmpeg_location"] == "C:/ffmpeg/bin"


@pytest.mark.parametrize(
    ("message", "expected_code"),
    [
        ("Unsupported URL: ftp://example.test/video", "unsupported_url"),
        ("Private video. Sign in if you've been granted access", "video_unavailable"),
        ("This video is unavailable", "video_unavailable"),
    ],
)
def test_ytdlp_acquirer_maps_download_errors(
    tmp_path,
    message: str,
    expected_code: str,
) -> None:
    class FailingDownloader(FakeDownloader):
        def extract_info(self, url: str, *, download: bool) -> dict[str, object]:
            del url, download
            raise RuntimeError(message)

    acquirer = YtDlpAcquirer(
        blob_store=LocalBlobStore(tmp_path / "blob"),
        media_locator="https://example.test/video",
        downloader_factory=FailingDownloader,
        work_dir=tmp_path / "work",
    )

    with pytest.raises(ResolveError) as exc:
        acquirer.download_proxy(uuid4())
    assert exc.value.code == expected_code
