"""Queue worker — pulls jobs from Valkey, runs ResearchLoop, emits SSE events."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from neo4j import AsyncDriver
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from axiom_core.enums import JobStatus
from axiom_core.settings import settings
from axiom_providers.valkey import ValkeyProvider

from .loop import ResearchLoop
from .synthesizer import sanitize_redis_report

log = logging.getLogger(__name__)

JOBS_KEY = "axiom:jobs"
QUEUE_KEY = "axiom:queue"

# Redis Streams key prefix for durable per-job event logs.
# Each job writes to  axiom:events:{job_id}  via XADD and reads back via XREAD.
EVENT_STREAM_KEY_PREFIX = "axiom:events"

# Bounded retention: keep the last N entries per job stream.
# Approximate trimming (MAXLEN ~) avoids expensive tree rebalancing on every
# write while keeping the stream within a few entries of the target length.
STREAM_MAXLEN: int = 500


def _channel(job_id: str) -> str:
    return f"axiom:stream:{job_id}"


def _event_stream_key(job_id: str) -> str:
    return f"{EVENT_STREAM_KEY_PREFIX}:{job_id}"


def _now() -> str:
    return datetime.now(UTC).isoformat()


class JobStore:
    """Thin helper for reading/writing job state in Valkey hashes."""

    def __init__(self, valkey: ValkeyProvider) -> None:
        self._v = valkey

    async def create(self, question: str) -> str:
        job_id = str(uuid.uuid4())
        payload = {
            "id": job_id,
            "question": question,
            "status": JobStatus.QUEUED.value,
            "created_at": _now(),
            "updated_at": _now(),
            "report": "",
            "error": "",
        }
        await self._v.client.hset(JOBS_KEY, job_id, json.dumps(payload))
        return job_id

    async def get(self, job_id: str) -> dict[str, Any] | None:
        raw = await self._v.client.hget(JOBS_KEY, job_id)
        return json.loads(raw) if raw else None

    async def list_all(self) -> list[dict[str, Any]]:
        all_raw = await self._v.client.hvals(JOBS_KEY)
        jobs = [json.loads(r) for r in all_raw]
        jobs.sort(key=lambda j: j["created_at"], reverse=True)
        return jobs

    async def update(self, job_id: str, **fields: Any) -> None:
        current = await self.get(job_id)
        if current is None:
            return
        current.update(fields)
        current["updated_at"] = _now()
        await self._v.client.hset(JOBS_KEY, job_id, json.dumps(current))


class StreamObserver:
    """Read-only helpers for inspecting per-job Redis Stream metadata.

    These are pure introspection calls — they never write to any stream.
    Use them from the observability router or the CLI script.
    """

    def __init__(self, valkey: ValkeyProvider) -> None:
        self._v = valkey

    async def stream_info(self, job_id: str) -> dict[str, Any] | None:
        """Return XINFO STREAM metadata for a single job stream.

        Returns None when the stream does not exist yet.
        Fields included:
          length         – current entry count
          first_entry_id – oldest entry ID (encodes ms timestamp)
          last_entry_id  – newest entry ID
          max_deleted_entry_id – highest trimmed ID (useful for auditing)
        """
        key = _event_stream_key(job_id)
        try:
            info = await self._v.client.xinfo_stream(key)
        except Exception:  # noqa: BLE001  — key may not exist
            return None

        return {
            "job_id": job_id,
            "stream_key": key,
            "length": info.get("length", 0),
            "first_entry_id": str(info.get("first-entry", ["?"])[0])
            if info.get("first-entry")
            else None,
            "last_entry_id": str(info.get("last-entry", ["?"])[0])
            if info.get("last-entry")
            else None,
            "max_deleted_entry_id": info.get("max-deleted-entry-id"),
            "stream_maxlen": STREAM_MAXLEN,
        }

    async def stream_stats(self, job_ids: list[str]) -> list[dict[str, Any]]:
        """Batch-fetch stream info for multiple jobs.

        Skips jobs with no stream yet (returns partial list — only jobs that
        have at least one event entry).
        """
        results = []
        for job_id in job_ids:
            info = await self.stream_info(job_id)
            if info is not None:
                results.append(info)
        return results


class QueueWorker:
    """Long-running coroutine that processes jobs from the Valkey queue."""

    def __init__(self, driver: AsyncDriver, valkey: ValkeyProvider) -> None:
        self._driver = driver
        self._valkey = valkey
        self._store = JobStore(valkey)
        self._running = False

    async def enqueue(self, question: str) -> str:
        """Add a job to the queue and return its ID."""
        job_id = await self._store.create(question)
        await self._valkey.client.rpush(QUEUE_KEY, job_id)
        return job_id

    async def _append_and_publish(
        self, job_id: str, event: str, data: Any
    ) -> None:
        """Append the event to the per-job Redis Stream AND publish to Pub/Sub.

        Writing to the Stream provides durable replay for late subscribers.
        Publishing to Pub/Sub provides low-latency fan-out for live subscribers.

        The stream is trimmed to STREAM_MAXLEN entries using approximate trimming
        (MAXLEN ~) so Redis never accumulates unbounded history per job.
        """
        payload = {"event": event, "data": data, "ts": _now()}
        msg = json.dumps(payload)
        stream_key = _event_stream_key(job_id)

        # XADD with MAXLEN ~ keeps the stream bounded at write time.
        # approximate=True maps to the "~" qualifier — Redis trims lazily at
        # radix-tree node boundaries, which is much cheaper than exact trimming.
        await self._valkey.client.xadd(
            stream_key,
            {"payload": msg},
            maxlen=STREAM_MAXLEN,
            approximate=True,
        )

        # Pub/Sub fan-out for live SSE subscribers
        await self._valkey.client.publish(_channel(job_id), msg)

    async def _process(self, job_id: str) -> None:
        await self._store.update(job_id, status=JobStatus.RUNNING.value)
        await self._append_and_publish(job_id, "status", {"status": "running"})
        try:
            job = await self._store.get(job_id)
            question = job["question"]  # type: ignore[index]

            await self._append_and_publish(
                job_id, "event", {"message": "Queued job picked up by worker"}
            )
            await self._append_and_publish(
                job_id, "event", {"message": "Planning research sub-queries"}
            )

            loop = ResearchLoop(self._driver)

            await self._append_and_publish(
                job_id, "event", {"message": "Running retrieval and extraction"}
            )
            result = await loop.run(
                question,
                job_id=job_id,
                breadth=settings.axiom_breadth,
            )

            await self._append_and_publish(
                job_id,
                "event",
                {"message": f"Collected {len(result.findings)} findings"},
            )
            for i, f in enumerate(result.findings, 1):
                await self._append_and_publish(
                    job_id,
                    "finding",
                    {"index": i, "sub_query": f.sub_query, "summary": f.summary[:200]},
                )

            await self._append_and_publish(
                job_id, "event", {"message": "Synthesized final report"}
            )
            clean_report = sanitize_redis_report(result.report)
            await self._store.update(
                job_id,
                status=JobStatus.DONE.value,
                report=clean_report,
            )
            await self._append_and_publish(
                job_id,
                "done",
                {"status": "done", "report": clean_report},
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("Job %s failed", job_id)
            await self._store.update(job_id, status=JobStatus.FAILED.value, error=str(exc))
            await self._append_and_publish(
                job_id, "error", {"message": str(exc), "error": str(exc)}
            )

    async def run_forever(self) -> None:
        """Block-wait on QUEUE_KEY and process jobs one at a time."""
        self._running = True
        log.info("QueueWorker started, listening on %s", QUEUE_KEY)
        while self._running:
            try:
                item = await self._valkey.client.blpop(QUEUE_KEY, timeout=2)
                if item is None:
                    continue
                _, job_id = item
                log.info("Processing job %s", job_id)
                await self._process(job_id)
            except asyncio.CancelledError:
                break
            except (RedisConnectionError, RedisTimeoutError):
                await asyncio.sleep(2)
            except Exception:  # noqa: BLE001
                log.exception("Unexpected error in worker loop")
                await asyncio.sleep(1)
        log.info("QueueWorker stopped")

    def stop(self) -> None:
        self._running = False


async def sse_stream(
    valkey: ValkeyProvider,
    job_id: str,
    last_id: str | None = None,
) -> AsyncIterator[str]:
    """Yield Server-Sent Events for a specific job.

    Strategy:
      1. Replay events from the Redis Stream.
         - If last_id is given (SSE reconnect via Last-Event-ID header or
           ?last_id query param), replay only events AFTER that ID so the
           client does not receive duplicates.
         - If last_id is absent, replay from the very beginning ("-").
      2. If the terminal event (done/error) is in the replay, return immediately.
      3. Otherwise subscribe to the Pub/Sub channel and forward live events.
         Each live event is tagged with an SSE "id:" line so the browser
         automatically tracks the cursor and sends Last-Event-ID on reconnect.

    The last_id value must be a valid Redis Stream entry ID
    (e.g. "1720000000000-0").  An invalid / unknown ID is safe — Redis XRANGE
    with an unknown exclusive start simply returns events from that point on,
    or nothing if the ID is beyond the latest entry.
    """
    client = valkey.client
    stream_key = _event_stream_key(job_id)

    # ------------------------------------------------------------------ #
    # 1. Replay the durable Redis Stream                                  #
    # ------------------------------------------------------------------ #
    # XRANGE returns [(entry_id, {field: value}), ...] in insertion order.
    # When last_id is provided, use exclusive start "(last_id" to skip the
    # already-seen entry.  When absent, start from "-" (very beginning).
    start = f"({last_id}" if last_id else "-"
    history: list[tuple[str, dict[str, str]]] = await client.xrange(
        stream_key, start, "+"
    )

    for entry_id, fields in history:
        raw = fields.get("payload", "")
        if not raw:
            continue
        # Emit the Redis Stream entry ID as the SSE event id so browsers can
        # send it back as Last-Event-ID on reconnect.
        yield f"id: {entry_id}\ndata: {raw}\n\n"
        try:
            parsed = json.loads(raw)
            if parsed.get("event") in ("done", "error"):
                # Job is already finished — no need to tail Pub/Sub.
                return
        except json.JSONDecodeError:
            pass

    # ------------------------------------------------------------------ #
    # 2. If stream is empty (and no last_id), seed an initial status      #
    # ------------------------------------------------------------------ #
    if not history and not last_id:
        job = await JobStore(valkey).get(job_id)
        if job:
            status = job["status"]
            payload = {"event": "status", "data": {"status": status}}
            yield f"data: {json.dumps(payload)}\n\n"
            if status in (JobStatus.DONE.value, JobStatus.FAILED.value):
                return

    # ------------------------------------------------------------------ #
    # 3. Tail live Pub/Sub messages for events not yet in the Stream      #
    # ------------------------------------------------------------------ #
    pubsub = client.pubsub()
    await pubsub.subscribe(_channel(job_id))
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            data_str = message["data"]
            yield f"data: {data_str}\n\n"
            try:
                parsed = json.loads(data_str)
                if parsed.get("event") in ("done", "error"):
                    break
            except json.JSONDecodeError:
                pass
    finally:
        await pubsub.unsubscribe(_channel(job_id))
        await pubsub.aclose()
