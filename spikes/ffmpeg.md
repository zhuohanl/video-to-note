# ffmpeg Spike

Date: 2026-06-06
Status: passed locally.

## Contract Locked

- `FrameSampler` can coarse-sample via `ffmpeg -vf fps=1`.
- Frame-on-demand can extract one frame via `ffmpeg -ss <timestamp> -frames:v 1`.
- The local machine has ffmpeg 8.1.1 installed by winget; current shells may need PATH refresh, or scripts can use `VTN_FFMPEG_PATH`.
- Harness generated a synthetic 3-second video, sampled 3 coarse frames, and extracted one exact timestamp frame.

## Command

`uv run python spikes/spike_ffmpeg.py`
