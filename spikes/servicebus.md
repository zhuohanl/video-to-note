# Azure Service Bus Spike

Date: 2026-06-06
Status: blocked for live run until Service Bus namespace/queue env vars are supplied.

## Contract Locked

- `QueueProvider` messages carry `job_id` and `attempt`.
- Real implementation must support send, receive, complete, and dead-letter.
- Duplicate delivery must be safe because worker stages are idempotent.

## Required Environment

- `AZURE_SERVICEBUS_FULLY_QUALIFIED_NAMESPACE`
- `AZURE_SERVICEBUS_QUEUE`

## Command

`RUN_REAL=1 uv run python spikes/spike_servicebus.py`
