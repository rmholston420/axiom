"""Job queue endpoints: create, list, get."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from redis.exceptions import ConnectionError, TimeoutError

from apps.api.dependencies import get_job_store, get_worker
from axiom_research.queue_worker import JobStore, QueueWorker

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobCreate(BaseModel):
    question: str
    breadth: int | None = None
    depth: int | None = None


class JobResponse(BaseModel):
    id: str
    question: str
    status: str
    created_at: str
    updated_at: str
    started_at: str = ""
    completed_at: str = ""
    elapsed_seconds: float | None = None
    query_id: str = ""
    axiom_id: str = ""
    wiki_page_id: str = ""
    wiki_status: str = ""
    wiki_error: str = ""
    report: str
    error: str


@router.post("", response_model=JobResponse, status_code=202)
async def create_job(
    body: JobCreate,
    worker: QueueWorker = Depends(get_worker),
    store: JobStore = Depends(get_job_store),
):
    """Enqueue a new research job."""
    job_id = await worker.enqueue(body.question, breadth=body.breadth, depth=body.depth)
    job = await store.get(job_id)
    return job


@router.get("", response_model=list[JobResponse])
async def list_jobs(store: JobStore = Depends(get_job_store)) -> list[JobResponse]:
    """Return all jobs, newest first."""
    try:
        return await store.list_all()
    except (ConnectionError, TimeoutError):
        return []


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, store: JobStore = Depends(get_job_store)):
    """Return a single job by ID."""
    job = await store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
