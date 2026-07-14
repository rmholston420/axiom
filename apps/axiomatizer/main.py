"""Axiom Axiomatizer — FastAPI service that proposes, evaluates, and stores axioms."""
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI

from apps.axiomatizer.routers import axiomatizer as axiomatizer_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

app = FastAPI(
    title="Axiom Axiomatizer",
    description="Axiom — Local Research Workbench axiom proposal, evaluation, and storage service",
    version="0.6.0",
)

app.include_router(axiomatizer_router.router)


@app.get("/")
async def root():
    return {"service": "Axiom Axiomatizer", "version": "0.6.0"}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "axiom-axiomatizer"}
