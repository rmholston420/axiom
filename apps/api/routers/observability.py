"""Stream observability router.

Exposes read-only metadata endpoints backed by Redis XLEN / XINFO STREAM so
you can inspect per-job event stream health without touching job state.

Endpoints
---------
GET /jobs/{job_id}/stream-info
    XINFO STREAM metadata for a single job: length, first/last entry IDs,
    max_deleted_entry_id (shows how many entries have been trimmed), and the
    configured STREAM_MAXLEN retention limit.

GET /streams/stats
    Batch metadata for all known jobs that have at least one stream entry.
    Sorted by stream length descending so the most active jobs surface first.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from apps.api.dependencies import get_job_store, get_valkey
from axiom_providers.valkey import ValkeyProvider
from axiom_research.queue_worker import JobStore, StreamObserver

router = APIRouter(tags=["observability"])


@router.get("/jobs/{job_id}/stream-info")
async def get_stream_info(
    job_id: str,
    store: JobStore = Depends(get_job_store),
    valkey: ValkeyProvider = Depends(get_valkey),
) -> dict[str, Any]:
    """Return Redis Stream metadata for a single job's event stream.

    Raises 404 if the job itself is unknown.
    Returns a 200 with ``length: 0`` placeholders if the job exists but has
    not yet emitted any stream entries.
    """
    job = await store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    observer = StreamObserver(valkey)
    info = await observer.stream_info(job_id)

    if info is None:
        # Job exists but stream has not been created yet (e.g. still queued)
        from axiom_research.queue_worker import STREAM_MAXLEN, _event_stream_key

        return {
            "job_id": job_id,
            "stream_key": _event_stream_key(job_id),
            "length": 0,
            "first_entry_id": None,
            "last_entry_id": None,
            "max_deleted_entry_id": None,
            "stream_maxlen": STREAM_MAXLEN,
        }

    return info


@router.get("/streams/stats")
async def get_all_stream_stats(
    store: JobStore = Depends(get_job_store),
    valkey: ValkeyProvider = Depends(get_valkey),
) -> list[dict[str, Any]]:
    """Return stream metadata for every job that has at least one stream entry.

    Jobs with no stream entries yet are omitted (they are typically still
    queued and will appear once the worker picks them up).

    Results are sorted by stream length descending — the most chatty jobs
    appear first, making it easy to spot jobs that are close to the retention
    limit or that emit an unusually high event volume.
    """
    all_jobs = await store.list_all()
    job_ids = [j["id"] for j in all_jobs]

    observer = StreamObserver(valkey)
    stats = await observer.stream_stats(job_ids)

    # Sort most-active first
    stats.sort(key=lambda s: s.get("length", 0), reverse=True)
    return stats
