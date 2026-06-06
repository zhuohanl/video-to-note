# Azure OpenAI Chat Spike

Date: 2026-06-06
Status: blocked for live run until Azure OpenAI endpoint/key/deployment env vars are supplied.

## Contract Locked

- `ChatModel.complete_json` uses an Azure OpenAI chat deployment through the OpenAI SDK.
- Structured JSON output should use `response_format={"type":"json_object"}` unless a stricter schema mechanism is validated in the live run.
- Invalid JSON must be retried before failing the stage.

## Required Environment

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_CHAT_DEPLOYMENT`

## Command

`RUN_REAL=1 uv run python spikes/spike_foundry_chat.py`
