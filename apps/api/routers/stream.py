"""SSE streaming endpoint for a single job.

`sse_stream` is an async generator — we adapt it with `_sse_generator` so that
FastAPI / Starlette's `StreamingResponse` receives a clean async iterable
rather than a raw generator, avoiding the common `TypeError: 'async_generator'
object is not iterable` error that surfaces when Starlette iterates directly.

Resume support
--------------
The SSE protocol sends a ``Last-Event-ID`` header on automatic reconnects.
We also accept an equivalent ``?last_id=`` query parameter for clients that
cannot set custom headers (e.g. ``<EventSource>`` in the browser).

When either is present, only events *after* that Redis Stream entry ID are
replayed, so a reconnecting client never receives duplicate events.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from fastapi.responses import StreamingResponse

from apps.api.dependencies import get_job_store, get_valkey
from axiom_providers.valkey import ValkeyProvider
from axiom_research.queue_worker import JobStore, sse_stream

router = APIRouter(prefix="/jobs", tags=["stream"])


async def _sse_generator(
    valkey: ValkeyProvider,
    job_id: str,
    last_id: str | None,
) -> AsyncIterator[str]:
    """Thin adaptor: consume the async generator and yield each chunk."""
    async for chunk in sse_stream(valkey, job_id, last_id=last_id):
        yield chunk


@router.get("/{job_id}/stream")
async def stream_job(
    job_id: str,
    store: JobStore = Depends(get_job_store),
    valkey: ValkeyProvider = Depends(get_valkey),
    # SSE standard reconnect header (browsers send this automatically)
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    # Query-param fallback for browser EventSource which cannot set headers
    last_id: str | None = Query(default=None),
):
    """Server-Sent Events stream for a job.

    Supports resume-from-last-event:
    - On reconnect the browser sends ``Last-Event-ID: <redis-stream-entry-id>``
      automatically (if the server emitted ``id:`` lines, which it now does).
    - Alternatively pass ``?last_id=<entry-id>`` as a query parameter.
    - Header takes precedence over query param when both are present.
    """
    job = await store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # Header takes precedence; fall back to query param.
    resume_from = last_event_id or last_id

    return StreamingResponse(
        _sse_generator(valkey, job_id, resume_from),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
