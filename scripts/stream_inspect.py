#!/usr/bin/env python
"""CLI script — inspect Redis Stream metadata for Axiom jobs.

Usage
-----
# All jobs that have stream entries, sorted by length desc
python scripts/stream_inspect.py

# Single job
python scripts/stream_inspect.py <job_id>

# Dump raw entries for a job (last N, default 20)
python scripts/stream_inspect.py <job_id> --tail 20

Requires AXIOM_REDIS_URL in the environment (or a .env file at repo root).
The script reads from Redis directly — no API server needed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Allow running from repo root without installing packages
sys.path.insert(0, str(Path(__file__).parent.parent))

import redis.asyncio as aioredis

JOBS_KEY = "axiom:jobs"
EVENT_STREAM_KEY_PREFIX = "axiom:events"


def _stream_key(job_id: str) -> str:
    return f"{EVENT_STREAM_KEY_PREFIX}:{job_id}"


async def _connect() -> aioredis.Redis:
    url = os.environ.get("AXIOM_REDIS_URL", "redis://localhost:6379")
    return aioredis.from_url(url, decode_responses=True)


async def inspect_all(r: aioredis.Redis) -> None:
    all_raw = await r.hvals(JOBS_KEY)
    if not all_raw:
        print("No jobs found in Valkey.")
        return

    rows: list[dict] = []
    for raw in all_raw:
        job = json.loads(raw)
        job_id = job["id"]
        key = _stream_key(job_id)
        length = await r.xlen(key)
        if length == 0:
            continue
        try:
            info = await r.xinfo_stream(key)
            first = info.get("first-entry", ["?"])[0] if info.get("first-entry") else "?"
            last = info.get("last-entry", ["?"])[0] if info.get("last-entry") else "?"
        except Exception:  # noqa: BLE001
            first = last = "?"
        rows.append({
            "job_id": job_id[:8] + "...",
            "status": job["status"],
            "length": length,
            "first_id": first,
            "last_id": last,
        })

    rows.sort(key=lambda r: r["length"], reverse=True)

    print(f"{'JOB ID':<14} {'STATUS':<10} {'LEN':>6}  {'FIRST ENTRY ID':<22}  {'LAST ENTRY ID':<22}")
    print("-" * 82)
    for row in rows:
        print(
            f"{row['job_id']:<14} {row['status']:<10} {row['length']:>6}"
            f"  {str(row['first_id']):<22}  {str(row['last_id']):<22}"
        )


async def inspect_job(
    r: aioredis.Redis, job_id: str, tail: int | None = None
) -> None:
    raw = await r.hget(JOBS_KEY, job_id)
    if not raw:
        print(f"Job {job_id!r} not found.")
        return

    job = json.loads(raw)
    key = _stream_key(job_id)
    length = await r.xlen(key)

    print(f"Job ID  : {job_id}")
    print(f"Question: {job['question']}")
    print(f"Status  : {job['status']}")
    print(f"Stream  : {key}")
    print(f"Length  : {length} entries")

    if tail and length > 0:
        entries = await r.xrevrange(key, "+", "-", count=tail)
        entries.reverse()  # chronological order
        print(f"\n--- last {len(entries)} entries ---")
        for entry_id, fields in entries:
            payload = json.loads(fields.get("payload", "{}"))
            print(f"  [{entry_id}] event={payload.get('event','?')}  "
                  f"data={json.dumps(payload.get('data', {}))[:120]}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect Axiom Redis Stream metadata")
    parser.add_argument("job_id", nargs="?", help="Specific job UUID (omit for all jobs)")
    parser.add_argument(
        "--tail", type=int, default=None,
        help="Also dump the last N stream entries for the given job",
    )
    args = parser.parse_args()

    r = await _connect()
    try:
        if args.job_id:
            await inspect_job(r, args.job_id, tail=args.tail)
        else:
            await inspect_all(r)
    finally:
        await r.aclose()


if __name__ == "__main__":
    asyncio.run(main())
