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

log = logging.getLogger(__name__)

JOBS_KEY = "axiom:jobs"
QUEUE_KEY = "axiom:queue"


def _channel(job_id: str) -> str:
    return f"axiom:stream:{job_id}"


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

    async def _publish(self, job_id: str, event: str, data: Any) -> None:
        msg = json.dumps({"event": event, "data": data, "ts": _now()})
        await self._valkey.client.publish(_channel(job_id), msg)

    async def _process(self, job_id: str) -> None:
        await self._store.update(job_id, status=JobStatus.RUNNING.value)
        await self._publish(job_id, "status", {"status": "running"})
        try:
            loop = ResearchLoop(self._driver)
            original_run = loop.run

            async def instrumented_run(question: str, **kwargs: Any):
                await self._publish(job_id, "progress", {"msg": "Planning sub-queries"})
                result = await original_run(question, job_id=job_id, **kwargs)
                for i, f in enumerate(result.findings, 1):
                    await self._publish(
                        job_id,
                        "finding",
                        {"index": i, "sub_query": f.sub_query, "summary": f.summary[:200]},
                    )
                return result

            job = await self._store.get(job_id)
            question = job["question"]  # type: ignore[index]
            result = await instrumented_run(
                question,
                breadth=settings.axiom_breadth,
            )
            await self._store.update(job_id, status=JobStatus.DONE.value, report=result.report)
            await self._publish(job_id, "done", {"status": "done", "report": result.report})
        except Exception as exc:  # noqa: BLE001
            log.exception("Job %s failed", job_id)
            await self._store.update(job_id, status=JobStatus.FAILED.value, error=str(exc))
            await self._publish(job_id, "error", {"error": str(exc)})

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


async def sse_stream(valkey: ValkeyProvider, job_id: str) -> AsyncIterator[str]:
    """Yield Server-Sent Events for a specific job.

    This is an async generator.  The StreamingResponse in `stream.py` wraps it
    with `_sse_generator` so that FastAPI receives a plain async iterator — the
    generator is consumed correctly regardless of starlette version.
    """
    pubsub = valkey.client.pubsub()
    await pubsub.subscribe(_channel(job_id))
    try:
        # Yield any already-stored status first
        job = await JobStore(valkey).get(job_id)
        if job:
            status = job["status"]
            yield f"data: {json.dumps({'event': 'status', 'data': {'status': status}})}\n\n"
            if status == JobStatus.DONE.value:
                payload = {
                    "event": "done",
                    "data": {"status": "done", "report": job.get("report", "")},
                }
                yield f"data: {json.dumps(payload)}\n\n"
                return
            if status == JobStatus.FAILED.value:
                payload = {
                    "event": "error",
                    "data": {"error": job.get("error", "unknown error")},
                }
                yield f"data: {json.dumps(payload)}\n\n"
                return
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            yield f"data: {message['data']}\n\n"
            parsed = json.loads(message["data"])
            if parsed.get("event") in ("done", "error"):
                break
    finally:
        await pubsub.unsubscribe(_channel(job_id))
        await pubsub.aclose()
