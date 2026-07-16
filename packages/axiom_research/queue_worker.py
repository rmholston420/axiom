"""Queue worker — pulls jobs from Valkey, runs ResearchLoop, emits SSE events.

Semantic SSE event protocol (Perplexity-style)
-----------------------------------------------
Every event is a JSON object written to both the Redis Stream (durable) and
Pub/Sub (live fan-out).  Each SSE frame carries an ``id:`` field so browsers
track Last-Event-ID automatically and resume without duplicates.

Lifecycle sequence per job::

    response.created          — job accepted, id assigned
    response.status           — status transitions (queued → running)
    response.searching        — one event per sub-query retrieval
    response.sources          — batch of sources found for a sub-query
    response.output_text.delta     — incremental text token from the model
    response.output_text.completed — full accumulated text (synthesis done)
    response.completed        — terminal success event with metadata
    error                     — terminal failure event

``response.completed`` now includes:
    elapsed_seconds  — total wall-clock seconds the job took
    started_at       — ISO-8601 UTC timestamp when the job began running
    completed_at     — ISO-8601 UTC timestamp when the job finished
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
import httpx
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
STREAM_MAXLEN: int = 2000


def _channel(job_id: str) -> str:
    return f"axiom:stream:{job_id}"


def _event_stream_key(job_id: str) -> str:
    return f"{EVENT_STREAM_KEY_PREFIX}:{job_id}"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _now_dt() -> datetime:
    return datetime.now(UTC)


def _elapsed(start: datetime) -> float:
    """Return wall-clock seconds since *start*, rounded to two decimal places."""
    return round((_now_dt() - start).total_seconds(), 2)


def _axiomatizer_base() -> str:
    return (
        getattr(settings, "axiom_axiomatizer_url", None)
        or f"http://axiom-api:{settings.axiom_api_port}"
    )


async def _persist_axiom_from_report(
    *,
    question: str,
    report: str,
) -> dict[str, Any] | None:
    if not settings.axiom_axiomatizer_enabled:
        return None

    report_text = (report or "").strip()
    if len(report_text) < 10:
        return None

    label_source = (question or "").strip() or "Research axiom"
    payload = {
        "source_text": report_text,
        "context": question,
        "label": label_source[:80],
    }

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(f"{_axiomatizer_base()}/axiomatizer", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else None
    except Exception as exc:  # noqa: BLE001
        log.warning("Axiomatizer persistence failed for question %r: %s", question, exc)
        return None


class JobStore:
    """Thin helper for reading/writing job state in Valkey hashes."""

    def __init__(self, valkey: ValkeyProvider) -> None:
        self._v = valkey

    async def create(self, question: str, breadth: int | None = None, depth: int | None = None) -> str:
        job_id = str(uuid.uuid4())
        payload = {
            "id": job_id,
            "question": question,
            "status": JobStatus.QUEUED.value,
            "created_at": _now(),
            "updated_at": _now(),
            "started_at": "",
            "completed_at": "",
            "elapsed_seconds": None,
            "axiom_id": "",
            "report": "",
            "error": "",
            "breadth": breadth,
            "depth": depth,
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
        """
        key = _event_stream_key(job_id)
        try:
            info = await self._v.client.xinfo_stream(key)
        except Exception:  # noqa: BLE001
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
        """Batch-fetch stream info for multiple jobs."""
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

    async def enqueue(self, question: str, breadth: int | None = None, depth: int | None = None) -> str:
        """Add a job to the queue and return its ID."""
        job_id = await self._store.create(question, breadth=breadth, depth=depth)
        await self._valkey.client.rpush(QUEUE_KEY, job_id)
        return job_id

    async def _append_and_publish(
        self, job_id: str, event: str, data: Any
    ) -> None:
        """Append the event to the per-job Redis Stream AND publish to Pub/Sub.

        The stream is trimmed to STREAM_MAXLEN entries using approximate trimming.
        """
        payload = {"event": event, "data": data, "ts": _now()}
        msg = json.dumps(payload)
        stream_key = _event_stream_key(job_id)

        await self._valkey.client.xadd(
            stream_key,
            {"payload": msg},
            maxlen=STREAM_MAXLEN,
            approximate=True,
        )
        await self._valkey.client.publish(_channel(job_id), msg)

    async def _process(self, job_id: str) -> None:  # noqa: C901
        """Run one job through the full pipeline, emitting semantic SSE events.

        Event sequence:
          response.created
          response.status (running)
          response.searching  x N sub-queries
          response.sources    x N sub-queries
          response.output_text.delta  x many (streaming tokens)
          response.output_text.completed
          response.completed  ← includes elapsed_seconds, started_at, completed_at
        On failure: error
        """
        # Record wall-clock start time for elapsed-time calculation.
        job_started_at: datetime = _now_dt()
        started_at_iso: str = job_started_at.isoformat()

        log.info("job=%s phase=process.start started_at=%s", job_id, started_at_iso)

        # Persist started_at immediately so the REST endpoint reflects it.
        await self._store.update(job_id, started_at=started_at_iso)

        # --- response.created ---
        await self._append_and_publish(
            job_id,
            "response.created",
            {"job_id": job_id},
        )

        await self._store.update(job_id, status=JobStatus.RUNNING.value)

        # --- response.status ---
        await self._append_and_publish(
            job_id,
            "response.status",
            {"status": "running"},
        )

        try:
            job = await self._store.get(job_id)
            question = job["question"]  # type: ignore[index]
            breadth = int(job.get("breadth") or settings.axiom_breadth)
            depth = int(job.get("depth") or 1)

            log.info(
                "job=%s phase=job.loaded breadth=%s depth=%s question=%r",
                job_id,
                breadth,
                depth,
                question,
            )

            # ------------------------------------------------------------------
            # Build a streaming-aware ResearchLoop by running the plan + retrieval
            # steps manually so we can emit per-sub-query events, then stream
            # the synthesis phase token-by-token.
            # ------------------------------------------------------------------
            from neo4j import AsyncDriver as _AD  # local import avoids circular
            from axiom_graph.repository import GraphRepository
            from axiom_graph.schema import ensure_schema
            from axiom_providers.ollama import OllamaProvider
            from axiom_providers.searxng import SearxngProvider
            from axiom_research.extractor import Extractor
            from axiom_research.models import RawFinding
            from axiom_research.planner import Planner
            from axiom_research.retriever import Retriever
            from axiom_research.synthesizer import Synthesizer, sanitize_redis_report

            ollama = OllamaProvider()
            searxng = SearxngProvider()
            planner = Planner(ollama)
            retriever = Retriever(searxng)
            extractor = Extractor(ollama)
            synthesizer = Synthesizer(ollama)

            await ensure_schema(self._driver)
            repo = GraphRepository(self._driver)
            query_id = await repo.create_query(question, job_id=job_id)

            # Plan sub-queries
            plan_started_at = _now_dt()
            log.info("job=%s phase=planner.start breadth=%s", job_id, breadth)
            sub_queries = await planner.plan(question, breadth=breadth)
            log.info(
                "job=%s phase=planner.done sub_queries=%s elapsed_seconds=%.2f",
                job_id,
                len(sub_queries),
                _elapsed(plan_started_at),
            )

            findings: list[RawFinding] = []

            for index, sq in enumerate(sub_queries, start=1):
                subquery_started_at = _now_dt()
                log.info(
                    "job=%s phase=subquery.start index=%s/%s query=%r",
                    job_id,
                    index,
                    len(sub_queries),
                    sq.text,
                )

                # --- response.searching ---
                await self._append_and_publish(
                    job_id,
                    "response.searching",
                    {"query": sq.text},
                )

                retrieval_started_at = _now_dt()
                log.info("job=%s phase=retrieval.start index=%s query=%r", job_id, index, sq.text)
                results = await retriever.retrieve(sq.text)
                log.info(
                    "job=%s phase=retrieval.done index=%s results=%s elapsed_seconds=%.2f",
                    job_id,
                    index,
                    len(results),
                    _elapsed(retrieval_started_at),
                )

                # Upsert sources into graph
                source_urls: list[str] = []
                sources_payload: list[dict[str, str]] = []
                for r in results:
                    await repo.upsert_source(url=r.url, title=r.title)
                    source_urls.append(r.url)
                    sources_payload.append({"title": r.title or "", "url": r.url or ""})

                # --- response.sources ---
                await self._append_and_publish(
                    job_id,
                    "response.sources",
                    {"query": sq.text, "sources": sources_payload},
                )

                extraction_started_at = _now_dt()
                log.info(
                    "job=%s phase=extractor.start index=%s query=%r result_count=%s",
                    job_id,
                    index,
                    sq.text,
                    len(results),
                )
                summary = await extractor.extract(sq.text, results)
                log.info(
                    "job=%s phase=extractor.done index=%s summary_chars=%s elapsed_seconds=%.2f",
                    job_id,
                    index,
                    len(summary or ""),
                    _elapsed(extraction_started_at),
                )

                graph_write_started_at = _now_dt()
                await repo.create_finding(
                    query_id=query_id,
                    sub_query=sq.text,
                    summary=summary,
                    source_urls=source_urls,
                )
                log.info(
                    "job=%s phase=graph_write.done index=%s sources=%s elapsed_seconds=%.2f",
                    job_id,
                    index,
                    len(source_urls),
                    _elapsed(graph_write_started_at),
                )
                log.info(
                    "job=%s phase=subquery.done index=%s/%s total_elapsed_seconds=%.2f",
                    job_id,
                    index,
                    len(sub_queries),
                    _elapsed(subquery_started_at),
                )

                findings.append(
                    RawFinding(
                        sub_query=sq.text,
                        summary=summary,
                        source_urls=source_urls,
                    )
                )

            # ------------------------------------------------------------------
            # Streaming synthesis: proxy token deltas directly to SSE.
            # ------------------------------------------------------------------
            accumulated: list[str] = []
            synthesis_started_at = _now_dt()
            delta_count = 0
            log.info(
                "job=%s phase=synthesis.start findings=%s",
                job_id,
                len(findings),
            )

            async for delta in synthesizer.synthesize_stream(question, findings):
                accumulated.append(delta)
                delta_count += 1
                if delta_count == 1 or delta_count % 25 == 0:
                    log.info(
                        "job=%s phase=synthesis.progress deltas=%s chars=%s elapsed_seconds=%.2f",
                        job_id,
                        delta_count,
                        sum(len(part) for part in accumulated),
                        _elapsed(synthesis_started_at),
                    )
                # --- response.output_text.delta ---
                await self._append_and_publish(
                    job_id,
                    "response.output_text.delta",
                    {"delta": delta},
                )

            full_report = sanitize_redis_report("".join(accumulated))
            log.info(
                "job=%s phase=synthesis.done deltas=%s report_chars=%s elapsed_seconds=%.2f",
                job_id,
                delta_count,
                len(full_report),
                _elapsed(synthesis_started_at),
            )

            axiomatizer_started_at = _now_dt()
            log.info("job=%s phase=axiomatizer.start enabled=%s", job_id, settings.axiom_axiomatizer_enabled)
            axiomatizer_result = await _persist_axiom_from_report(
                question=question,
                report=full_report,
            )
            log.info(
                "job=%s phase=axiomatizer.done elapsed_seconds=%.2f",
                job_id,
                _elapsed(axiomatizer_started_at),
            )
            axiom_id = ""
            if isinstance(axiomatizer_result, dict):
                axiom_id = str(
                    axiomatizer_result.get("axiom_id")
                    or axiomatizer_result.get("axiomid")
                    or ""
                )

            # --- response.output_text.completed ---
            await self._append_and_publish(
                job_id,
                "response.output_text.completed",
                {"text": full_report},
            )

            # Compute elapsed time now that all work is done.
            elapsed: float = _elapsed(job_started_at)
            completed_at_iso: str = _now()

            await self._store.update(
                job_id,
                status=JobStatus.DONE.value,
                report=full_report,
                elapsed_seconds=elapsed,
                completed_at=completed_at_iso,
                axiom_id=axiom_id,
            )
            log.info(
                "job=%s phase=process.done finding_count=%s report_chars=%s elapsed_seconds=%.2f axiom_id=%r",
                job_id,
                len(findings),
                len(full_report),
                elapsed,
                axiom_id,
            )

            # --- response.completed (terminal) ---
            await self._append_and_publish(
                job_id,
                "response.completed",
                {
                    "status": "done",
                    "report": full_report,
                    "finding_count": len(findings),
                    "query_id": str(query_id),
                    "elapsed_seconds": elapsed,
                    "started_at": started_at_iso,
                    "completed_at": completed_at_iso,
                    "axiom_id": axiom_id,
                },
            )

        except Exception as exc:  # noqa: BLE001
            log.exception("job=%s phase=process.failed error=%s", job_id, exc)
            elapsed_on_error: float = _elapsed(job_started_at)
            completed_at_iso_err: str = _now()
            await self._store.update(
                job_id,
                status=JobStatus.FAILED.value,
                error=str(exc),
                elapsed_seconds=elapsed_on_error,
                completed_at=completed_at_iso_err,
            )
            # --- error (terminal) ---
            await self._append_and_publish(
                job_id,
                "error",
                {
                    "message": str(exc),
                    "error": str(exc),
                    "elapsed_seconds": elapsed_on_error,
                    "started_at": started_at_iso,
                    "completed_at": completed_at_iso_err,
                },
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
      1. Replay events from the Redis Stream (with dedup via last_id).
      2. If a terminal event (response.completed / error) is in the replay,
         return immediately.
      3. Otherwise subscribe to Pub/Sub and forward live events.

    Every SSE frame carries an ``id:`` line set to the Redis Stream entry ID
    so browsers track Last-Event-ID and resume without duplicating chunks.
    """
    client = valkey.client
    stream_key = _event_stream_key(job_id)

    # 1. Replay durable Redis Stream
    start = f"({last_id}" if last_id else "-"
    history: list[tuple[str, dict[str, str]]] = await client.xrange(
        stream_key, start, "+"
    )

    TERMINAL_EVENTS = {"response.completed", "error"}

    for entry_id, fields in history:
        raw = fields.get("payload", "")
        if not raw:
            continue
        yield f"id: {entry_id}\ndata: {raw}\n\n"
        try:
            parsed = json.loads(raw)
            if parsed.get("event") in TERMINAL_EVENTS:
                return
        except json.JSONDecodeError:
            pass

    # 2. Seed an initial status event for late subscribers with no history
    if not history and not last_id:
        job = await JobStore(valkey).get(job_id)
        if job:
            status = job["status"]
            payload = {"event": "response.status", "data": {"status": status}}
            yield f"data: {json.dumps(payload)}\n\n"
            if status in (JobStatus.DONE.value, JobStatus.FAILED.value):
                return

    # 3. Tail live Pub/Sub for events not yet in the Stream
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
                if parsed.get("event") in TERMINAL_EVENTS:
                    break
            except json.JSONDecodeError:
                pass
    finally:
        await pubsub.unsubscribe(_channel(job_id))
        await pubsub.aclose()
