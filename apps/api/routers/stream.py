"""SSE streaming endpoint for a single job.

`sse_stream` is an async generator — we adapt it with `_sse_generator` so that
FastAPI / Starlette's `StreamingResponse` receives a clean async iterable
rather than a raw generator, avoiding the common `TypeError: 'async_generator'
object is not iterable` error that surfaces when Starlette iterates directly.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from apps.api.dependencies import get_job_store, get_valkey
from axiom_providers.valkey import ValkeyProvider
from axiom_research.queue_worker import JobStore, sse_stream

router = APIRouter(prefix="/jobs", tags=["stream"])


async def _sse_generator(valkey: ValkeyProvider, job_id: str) -> AsyncIterator[str]:
    """Thin adaptor: consume the async generator and yield each chunk."""
    async for chunk in sse_stream(valkey, job_id):
        yield chunk


@router.get("/{job_id}/stream")
async def stream_job(
    job_id: str,
    store: JobStore = Depends(get_job_store),
    valkey: ValkeyProvider = Depends(get_valkey),
):
    """Server-Sent Events stream for a job."""
    job = await store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return StreamingResponse(
        _sse_generator(valkey, job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
