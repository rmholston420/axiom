"""E2E test helpers: ensure Axiom API is reachable before running."""

import os

import httpx
import pytest

AXIOM_API_URL = os.getenv("AXIOM_API_URL", "http://localhost:7200")


@pytest.fixture(scope="session", autouse=True)
def ensure_axiom_api_reachable():
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(AXIOM_API_URL + "/health")
        if resp.status_code != 200:
            pytest.skip(f"Axiom API not healthy at {AXIOM_API_URL}/health (status {resp.status_code})")
    except Exception:
        pytest.skip(f"Axiom API not reachable at {AXIOM_API_URL}")
