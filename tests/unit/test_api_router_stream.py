import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.dependencies import get_job_store, get_valkey
from apps.api.routers import stream as stream_router
from apps.api.routers.stream import router


class DummyStore:
    def __init__(self, job=None):
        self.job = job
        self.calls = []

    async def get(self, job_id):
        self.calls.append(job_id)
        return self.job


class DummyValkey:
    pass


def make_app(store, valkey):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_job_store] = lambda: store
    app.dependency_overrides[get_valkey] = lambda: valkey
    return app


def sample_job():
    return {
        "id": "job-123",
        "question": "What is Axiom?",
        "status": "running",
        "created_at": "2026-07-15T12:00:00Z",
        "updated_at": "2026-07-15T12:00:00Z",
        "report": "",
        "error": "",
    }


@pytest.mark.unit
def test_stream_job_returns_404_when_job_missing():
    store = DummyStore(job=None)
    client = TestClient(make_app(store, DummyValkey()))

    response = client.get("/jobs/job-404/stream")

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}
    assert store.calls == ["job-404"]


@pytest.mark.unit
def test_stream_job_returns_sse_response(monkeypatch):
    called = {}

    async def fake_sse_stream(valkey, job_id):
        called["valkey"] = valkey
        called["job_id"] = job_id
        yield b"data: hello\n\n"
        yield b"data: world\n\n"

    monkeypatch.setattr(stream_router, "sse_stream", fake_sse_stream)

    store = DummyStore(job=sample_job())
    valkey = DummyValkey()
    client = TestClient(make_app(store, valkey))

    with client.stream("GET", "/jobs/job-123/stream") as response:
        body = b"".join(response.iter_bytes())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    assert body == b"data: hello\n\ndata: world\n\n"
    assert store.calls == ["job-123"]
    assert called["valkey"] is valkey
    assert called["job_id"] == "job-123"
