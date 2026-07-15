"""FastAPI dependency injection: Neo4j driver, Valkey client, JobStore, QueueWorker."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from neo4j import AsyncGraphDatabase

from axiom_core.settings import settings
from axiom_providers.valkey import ValkeyProvider
from axiom_research.queue_worker import JobStore, QueueWorker

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: open connections and launch worker. Shutdown: close everything."""
    # Neo4j
    driver = AsyncGraphDatabase.driver(
        settings.axiom_neo4j_uri,
        auth=(settings.axiom_neo4j_user, settings.axiom_neo4j_password),
    )
    # Valkey
    valkey = ValkeyProvider()
    # Worker
    worker = QueueWorker(driver=driver, valkey=valkey)
    worker_task = asyncio.create_task(worker.run_forever())

    app.state.driver = driver
    app.state.valkey = valkey
    app.state.job_store = JobStore(valkey)
    app.state.worker = worker

    log.info("Axiom API startup complete")
    yield

    # Shutdown
    worker.stop()
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    await valkey.aclose()
    await driver.close()
    log.info("Axiom API shutdown complete")


async def get_driver(request: Request):
    return request.app.state.driver


async def get_valkey(request: Request) -> ValkeyProvider:
    return request.app.state.valkey


async def get_job_store(request: Request) -> JobStore:
    return request.app.state.job_store


async def get_worker(request: Request) -> QueueWorker:
    return request.app.state.worker
