"""E2E test helpers: ensure Axiom API is reachable before running."""

from __future__ import annotations

import os
import subprocess

import httpx
import pytest

AXIOM_API_URL = os.getenv("AXIOM_API_URL", "http://localhost:7200")


def _compose_services() -> set[str]:
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--services"],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return set()
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


@pytest.fixture(scope="session", autouse=True)
def ensure_axiom_api_reachable() -> None:
    services = _compose_services()
    if services and "axiom-worker" not in services:
        pytest.skip("Axiom worker service is not present in docker compose")

    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(AXIOM_API_URL + "/health")
        if resp.status_code != 200:
            pytest.skip(
                f"Axiom API not healthy at {AXIOM_API_URL}/health (status {resp.status_code})"
            )
    except Exception:
        pytest.skip(f"Axiom API not reachable at {AXIOM_API_URL}")
