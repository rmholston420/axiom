"""Axiom API — FastAPI application entry point."""
import sys
import os

# Make packages importable when running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI
from apps.api.routers import health

app = FastAPI(
    title="Axiom API",
    description="Axiom — Local Research Workbench",
    version="0.1.0",
)

app.include_router(health.router)


@app.get("/")
async def root():
    return {"service": "Axiom API", "version": "0.1.0"}
