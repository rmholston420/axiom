"""SSE streaming endpoint for a single job."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from apps.api.dependencies import get_job_store, get_valkey
from axiom_providers.valkey import ValkeyProvider
from axiom_research.queue_worker import JobStore, sse_stream

router = APIRouter(prefix="/jobs", tags=["stream"])


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
        sse_stream(valkey, job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
