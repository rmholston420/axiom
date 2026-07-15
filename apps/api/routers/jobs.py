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


class JobResponse(BaseModel):
    id: str
    question: str
    status: str
    created_at: str
    updated_at: str
    report: str
    error: str


@router.post("", response_model=JobResponse, status_code=202)
async def create_job(
    body: JobCreate,
    worker: QueueWorker = Depends(get_worker),
    store: JobStore = Depends(get_job_store),
):
    """Enqueue a new research job."""
    job_id = await worker.enqueue(body.question)
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
