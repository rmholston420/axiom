"""E2E test: submit a research job and verify it completes with a report.

This test is slow (depends on Ollama inference time) and is marked `e2e`.
Run with: pytest -m e2e
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import httpx
import pytest

AXIOM_API_URL = os.getenv("AXIOM_API_URL", "http://localhost:7200")
FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "sample_job.json"
E2E_TIMEOUT = int(os.getenv("AXIOM_E2E_TIMEOUT", "120"))


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_research_job_completes() -> None:
    """Submit a job, poll until done, confirm report is non-empty."""
    payload = json.loads(FIXTURE_PATH.read_text())

    async with httpx.AsyncClient(timeout=30) as client:
        # Submit job
        resp = await client.post(f"{AXIOM_API_URL}/jobs", json=payload)
        assert resp.status_code in (200, 201, 202), f"Job creation failed: {resp.text}"
        job = resp.json()
        job_id = job.get("id") or job.get("job_id")
        assert job_id, "Response missing job id"

        # Poll until complete or timeout
        deadline = asyncio.get_event_loop().time() + E2E_TIMEOUT
        poll_count = 0
        while asyncio.get_event_loop().time() < deadline:
            status_resp = await client.get(f"{AXIOM_API_URL}/jobs/{job_id}")
            status_resp.raise_for_status()
            data = status_resp.json()
            state = data.get("status") or data.get("state", "")
            poll_count += 1
            if poll_count % 5 == 0:
                # Lightweight debug logging to aid future e2e diagnosis
                print(f"[e2e] poll {poll_count}: job_id={job_id} state={state!r}")
            if state in ("done", "complete", "completed", "finished"):
                report = data.get("report") or data.get("result", "")
                assert report, "Job completed but report is empty"
                return
            if state in ("error", "failed"):
                pytest.fail(f"Job failed: {data}")
            await asyncio.sleep(3)

        pytest.fail(f"Job did not complete within {E2E_TIMEOUT}s")
