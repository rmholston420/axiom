"""Integration smoke tests — verify all Axiom services respond on their health endpoints.

These tests run against a live stack (docker compose up -d or local dev).
Set AXIOM_API_URL, AXIOM_COUNCIL_URL, AXIOM_AXIOMATIZER_URL env vars to
override the defaults.
"""
from __future__ import annotations

import os

import httpx
import pytest

AXIOM_API_URL = os.getenv("AXIOM_API_URL", "http://localhost:7200")
AXIOM_COUNCIL_URL = os.getenv("AXIOM_COUNCIL_URL", "http://localhost:7201")
AXIOM_AXIOMATIZER_URL = os.getenv("AXIOM_AXIOMATIZER_URL", "http://localhost:7202")
AXIOM_WEB_URL = os.getenv("AXIOM_WEB_URL", "http://localhost:7100")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_health() -> None:
    """Axiom API /health returns 200."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{AXIOM_API_URL}/health")
    assert resp.status_code == 200, f"API health failed: {resp.text}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_council_health() -> None:
    """Axiom Council /health returns 200."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{AXIOM_COUNCIL_URL}/health")
    assert resp.status_code == 200, f"Council health failed: {resp.text}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_axiomatizer_health() -> None:
    """Axiom Axiomatizer /health returns 200."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{AXIOM_AXIOMATIZER_URL}/health")
    assert resp.status_code == 200, f"Axiomatizer health failed: {resp.text}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_web_root() -> None:
    """Axiom Web root returns 200."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(AXIOM_WEB_URL)
    assert resp.status_code == 200, f"Web root failed: {resp.text}"
