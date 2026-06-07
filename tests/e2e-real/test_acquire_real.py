from __future__ import annotations

import os
from uuid import uuid4

import pytest
from vtn_ingest.ytdlp_acquirer import YtDlpAcquirer
from vtn_storage.blob import LocalBlobStore


@pytest.mark.real_infra
def test_acquire_real_downloads_playable_sized_proxy(tmp_path) -> None:
    if os.environ.get("RUN_REAL") != "1":
        pytest.skip("set RUN_REAL=1 to run live yt-dlp acquisition")

    url = os.environ.get(
        "VTN_REAL_VIDEO_URL",
        "https://www.youtube.com/watch?v=jNQXAC9IVRw",
    )
    blob_store = LocalBlobStore(tmp_path / "blob")
    artifact = YtDlpAcquirer(
        blob_store=blob_store,
        media_locator=url,
        work_dir=tmp_path / "work",
        ffmpeg_location=os.environ.get("FFMPEG_LOCATION"),
    ).download_proxy(uuid4())

    data = blob_store.get(artifact.blob_path)
    assert artifact.blob_path.endswith(".mp4")
    assert len(data) > 10_000
