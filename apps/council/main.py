"""Axiom Council — FastAPI service that runs sequential or parallel model fan-out."""
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI

from apps.council.routers import council as council_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

app = FastAPI(
    title="Axiom Council",
    description="Axiom — Local Research Workbench council fan-out and synthesis service",
    version="0.6.0",
)

app.include_router(council_router.router)


@app.get("/")
async def root():
    return {"service": "Axiom Council", "version": "0.6.0"}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "axiom-council"}
