"""Axiom API — FastAPI application entry point (Slice 7: stream observability added)."""

import logging

from fastapi import FastAPI

from apps.api.dependencies import lifespan
from apps.api.routers import axiomatizer, council, graph, health, jobs, observability, stream, wiki
from apps.api.routers import models as models_router
from apps.api.routers import settings as settings_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

app = FastAPI(
    title="Axiom API",
    description="Axiom — Local Research Workbench",
    version="0.7.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(jobs.router)
app.include_router(stream.router)
app.include_router(observability.router)
app.include_router(settings_router.router)
app.include_router(models_router.router)
app.include_router(graph.router)
app.include_router(council.router)
app.include_router(axiomatizer.router)
app.include_router(wiki.router)


@app.get("/")
async def root():
    return {"service": "Axiom API", "version": "0.7.0"}
