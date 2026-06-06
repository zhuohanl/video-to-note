# yt-dlp Spike

Date: 2026-06-06
Status: passed against `https://www.youtube.com/watch?v=jNQXAC9IVRw`.

## Contract Locked

- `MediaAcquirer.download_proxy` uses yt-dlp with format selector `bv*[height<=720]+ba/b[height<=720]/b`.
- Section download uses `download_sections=["*0-30"]` for tiny acceptance clips and `ffmpeg_location` when ffmpeg is not on PATH.
- Expected failure mapping: unsupported extractor → `unsupported_url`; unavailable/private/age-gated media → `video_unavailable`.
- The previous yt-dlp test URL `BaW_jenozKc` returned video unavailable in this environment; `jNQXAC9IVRw` succeeded.
- yt-dlp warned that no JavaScript runtime was detected; extraction still succeeded, but production should allow configuring a JS runtime if YouTube begins requiring it.

## Command

`RUN_REAL=1 VTN_SPIKE_VIDEO_URL=https://www.youtube.com/watch?v=jNQXAC9IVRw uv run python spikes/spike_ytdlp.py`
