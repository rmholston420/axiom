"""Integration tests for Axiom API REST endpoints."""

from __future__ import annotations

import os

import httpx
import pytest

AXIOM_API_URL = os.getenv("AXIOM_API_URL", "http://localhost:7200")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_jobs_returns_list() -> None:
    """GET /jobs returns a JSON list."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{AXIOM_API_URL}/jobs")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_settings_returns_dict() -> None:
    """GET /settings returns a JSON object."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{AXIOM_API_URL}/settings")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_models_returns_payload_with_models_list() -> None:
    """GET /models returns an object containing a models list."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{AXIOM_API_URL}/models")
    assert resp.status_code == 200
    payload = resp.json()
    assert isinstance(payload, dict)
    assert "models" in payload
    assert isinstance(payload["models"], list)
