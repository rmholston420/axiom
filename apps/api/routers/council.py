"""Axiom API — Council proxy router.

Forwards POST /council requests to apps/council over HTTP so service
boundaries are preserved (no direct import of council code).
"""
from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from axiom_core.settings import settings

log = logging.getLogger(__name__)

router = APIRouter(prefix="/council", tags=["council"])

_COUNCIL_BASE = f"http://127.0.0.1:{settings.axiom_council_port}"


class CouncilProxyRequest(BaseModel):
    question: str
    context: str = ""
    council_size: int = Field(default=0, ge=0, le=10)
    mode: Literal["sequential", "parallel"] = "sequential"


@router.post("")
async def proxy_council(body: CouncilProxyRequest):
    """Proxy council request to the Axiom Council service."""
    if not settings.axiom_council_enabled:
        raise HTTPException(status_code=503, detail="Council is disabled via AXIOM_COUNCIL_ENABLED")

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{_COUNCIL_BASE}/council",
                json=body.model_dump(),
            )
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        log.error("Council service unreachable at %s", _COUNCIL_BASE)
        raise HTTPException(
            status_code=503,
            detail=f"Axiom Council service is not reachable at {_COUNCIL_BASE}. "
                   "Start it with: make council",
        )
    except httpx.HTTPStatusError as exc:
        log.error("Council returned %s: %s", exc.response.status_code, exc.response.text)
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=exc.response.text,
        )
