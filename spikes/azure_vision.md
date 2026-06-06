# Azure Vision / Document Intelligence OCR Spike

Date: 2026-06-06
Status: blocked for live run until Vision/Document Intelligence resource env vars are supplied.

## Contract Locked

- `OcrProvider.extract` returns OCR text plus optional bounding boxes.
- OCR failures are non-blocking warnings during visual indexing.
- Frame size/rate limits are provider-specific and must be recorded after live run.

## Required Environment

- `AZURE_VISION_ENDPOINT`
- `AZURE_VISION_KEY`
- `VTN_SPIKE_FRAME_PATH`

## Command

`RUN_REAL=1 uv run python spikes/spike_azure_vision.py`
