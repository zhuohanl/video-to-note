# Azure OpenAI Embeddings Spike

Date: 2026-06-06
Status: blocked for live run until Azure OpenAI embedding deployment env vars are supplied.

## Contract Locked

- `EmbeddingModel.embed` batches strings and returns one vector per input.
- Dimension and batch limit must be recorded after live run.

## Required Environment

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_EMBED_DEPLOYMENT`

## Command

`RUN_REAL=1 uv run python spikes/spike_foundry_embeddings.py`
