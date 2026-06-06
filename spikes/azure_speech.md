# Azure Speech ASR Spike

Date: 2026-06-06
Status: blocked for live run until Speech resource and sample audio env vars are supplied.

## Contract Locked

- `AzureSpeechProvider.fetch` returns normalized transcript spans with start/end seconds and text.
- Speaker labels are optional and must degrade gracefully when unavailable.
- Timeout/failure emits an ASR warning or `transcript_failed` depending on provider-chain state.

## Required Environment

- `AZURE_SPEECH_KEY`
- `AZURE_SPEECH_REGION`
- `VTN_SPIKE_AUDIO_PATH`

## Command

`RUN_REAL=1 uv run python spikes/spike_azure_speech.py`
