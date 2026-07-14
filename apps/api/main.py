"""Axiom API — FastAPI application entry point (Slice 6: axiomatizer proxy added)."""
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI

from apps.api.dependencies import lifespan
from apps.api.routers import council
from apps.api.routers import axiomatizer
from apps.api.routers import graph
from apps.api.routers import health
from apps.api.routers import jobs
from apps.api.routers import models as models_router
from apps.api.routers import settings as settings_router
from apps.api.routers import stream

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

app = FastAPI(
    title="Axiom API",
    description="Axiom — Local Research Workbench",
    version="0.6.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(jobs.router)
app.include_router(stream.router)
app.include_router(settings_router.router)
app.include_router(models_router.router)
app.include_router(graph.router)
app.include_router(council.router)
app.include_router(axiomatizer.router)


@app.get("/")
async def root():
    return {"service": "Axiom API", "version": "0.6.0"}
