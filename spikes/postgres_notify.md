# Postgres LISTEN/NOTIFY + Advisory Lock Spike

Date: 2026-06-06
Status: passed locally.

## Contract Locked

- Canonical URL claiming can be serialized with `pg_advisory_xact_lock(hashtext(url))`.
- API SSE replay can use `LISTEN/NOTIFY` as a wake-up channel over the append-only `job_events` table.
- `job_events.id` remains the durable SSE id; NOTIFY payload is only a hint to fetch rows.
- Local direct test uses `TEST_DATABASE_URL=postgresql://vtn:vtn@127.0.0.1:55432/vtn` by default because this machine has another Postgres listener on 5432.

## Command

`uv run python spikes/spike_postgres_notify.py`
