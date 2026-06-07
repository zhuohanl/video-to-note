from __future__ import annotations

import asyncio
import json
import os
from uuid import uuid4

import asyncpg


async def _run() -> dict[str, object]:
    database_url = os.environ.get("TEST_DATABASE_URL", "postgresql://vtn:vtn@127.0.0.1:55432/vtn")
    connection = await asyncpg.connect(database_url)
    listener = await asyncpg.connect(database_url)
    received: asyncio.Queue[str] = asyncio.Queue()
    channel = f"vtn_spike_{uuid4().hex}"

    async def callback(
        connection: asyncpg.Connection,
        pid: int,
        channel: str,
        payload: str,
    ) -> None:
        del connection, pid, channel
        await received.put(payload)

    try:
        await listener.add_listener(channel, callback)
        async with connection.transaction():
            await connection.execute("SELECT pg_advisory_xact_lock(hashtext($1))", "https://example.com/video")
            inserted = await connection.fetchval(
                """
                WITH attempted AS (
                    SELECT $1::text AS canonical_url
                )
                SELECT canonical_url FROM attempted
                """,
                "https://example.com/video",
            )
            await connection.execute(f"NOTIFY {channel}, 'job_events:1'")
        payload = await asyncio.wait_for(received.get(), timeout=5)
        return {"advisory_lock": True, "canonical_claim": inserted, "notify_payload": payload}
    finally:
        await listener.close()
        await connection.close()


def main() -> int:
    print(json.dumps(asyncio.run(_run()), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
