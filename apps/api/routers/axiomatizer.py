"""Axiom API — Axiomatizer proxy router."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from axiom_core.settings import settings

log = logging.getLogger(__name__)

router = APIRouter(prefix="/axiomatizer", tags=["axiomatizer"])

_AXIOMATIZER_BASE = (
    getattr(settings, "axiom_axiomatizer_url", None)
    or f"http://axiom-axiomatizer:{settings.axiom_axiomatizer_port}"
)


class AxiomProxyRequest(BaseModel):
    source_text: str = Field(..., min_length=10)
    context: str = ""
    label: str = ""


@router.post("")
async def proxy_axiomatizer(body: AxiomProxyRequest):
    if not settings.axiom_axiomatizer_enabled:
        raise HTTPException(
            status_code=503,
            detail="Axiomatizer is disabled. Set AXIOM_AXIOMATIZER_ENABLED=true to enable.",
        )
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(f"{_AXIOMATIZER_BASE}/axiomatizer", json=body.model_dump())
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        log.error("Axiomatizer service unreachable at %s", _AXIOMATIZER_BASE)
        raise HTTPException(
            status_code=503,
            detail=(
                "Axiom Axiomatizer service is not reachable at "
                f"{_AXIOMATIZER_BASE}. Start it with: make axiomatizer"
            ),
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)


@router.get("/axioms")
async def proxy_list_axioms(limit: int = Query(default=50, ge=1, le=500)):
    if not settings.axiom_axiomatizer_enabled:
        raise HTTPException(status_code=503, detail="Axiomatizer is disabled.")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{_AXIOMATIZER_BASE}/axiomatizer/axioms", params={"limit": limit}
            )
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=f"Axiom Axiomatizer service is not reachable at {_AXIOMATIZER_BASE}.",
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
