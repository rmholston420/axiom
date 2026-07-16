from __future__ import annotations

import json
from typing import Any

from fastapi.testclient import TestClient

from apps.api.dependencies import get_driver, get_job_store, get_valkey, get_worker
from apps.api.main import app
from axiom_core.enums import JobStatus
from axiom_research.queue_worker import JobStore, QueueWorker


class DummyResult:
    def __init__(self, rows):
        self._rows = rows

    def __aiter__(self):
        self._iter = iter(self._rows)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


class DummySession:
    def __init__(self, rows):
        self.rows = rows
        self.run_calls = []

    async def run(self, cypher):
        self.run_calls.append(cypher)
        return DummyResult(self.rows)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummyDriver:
    def __init__(self, node_rows=None, edge_rows=None):
        self.node_rows = node_rows or []
        self.edge_rows = edge_rows or []
        self.calls = 0

    def session(self):
        self.calls += 1
        if self.node_rows and self.calls == 1:
            return DummySession(self.node_rows)
        return DummySession(self.edge_rows)

    async def close(self) -> None:
        return


class DummyValkeyClient:
    """Minimal fake PubSub + list operations for SSE + jobs tests."""

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self.pubsub_instance = DummyPubSub()

    async def hset(self, key: str, field: str, value: str) -> None:
        if key != "axiom:jobs":
            return
        self._jobs[field] = json.loads(value)

    async def hget(self, key: str, field: str) -> str | None:
        if key != "axiom:jobs":
            return None
        job = self._jobs.get(field)
        return json.dumps(job) if job else None

    async def hvals(self, key: str) -> list[str]:
        if key != "axiom:jobs":
            return []
        return [json.dumps(j) for j in self._jobs.values()]

    async def rpush(self, key: str, value: str) -> None:
        return

    async def publish(self, channel: str, message: str) -> None:
        self.pubsub_instance.messages.append(
            {"type": "message", "data": message, "channel": channel}
        )

    async def xrange(self, key: str, min: str = "-", max: str = "+", count: int | None = None):
        return []

    def pubsub(self) -> "DummyPubSub":
        return self.pubsub_instance


class DummyPubSub:
    def __init__(self) -> None:
        self.subscribed: list[str] = []
        self.unsubscribed: list[str] = []
        self.messages: list[dict[str, Any]] = []

    async def subscribe(self, channel: str) -> None:
        self.subscribed.append(channel)

    async def unsubscribe(self, channel: str) -> None:
        self.unsubscribed.append(channel)

    async def aclose(self) -> None:
        return

    async def listen(self):
        for msg in list(self.messages):
            yield msg


class DummyValkey:
    """Minimal valkey-like object exposing the interface the app uses."""

    def __init__(self) -> None:
        self._client = DummyValkeyClient()

    @property
    def client(self) -> DummyValkeyClient:
        return self._client

    async def aclose(self) -> None:
        return


class DummyWorker(QueueWorker):
    """QueueWorker that never touches real ResearchLoop."""

    def __init__(self, store: JobStore, valkey: DummyValkey) -> None:
        super().__init__(driver=object(), valkey=valkey)
        self._store = store

    async def enqueue(self, question: str, breadth: int | None = None, depth: int | None = None) -> str:
        job_id = await self._store.create(question, breadth=breadth, depth=depth)
        return job_id

    async def run_forever(self) -> None:  # pragma: no cover
        return


def _make_app_with_overrides() -> TestClient:
    """Return a TestClient with dummy Valkey + JobStore + QueueWorker wired via overrides."""
    dummy_valkey = DummyValkey()
    store = JobStore(dummy_valkey)
    worker = DummyWorker(store, dummy_valkey)
    driver = DummyDriver(
        node_rows=[
            {"id": "n1", "label": "Node 1", "type": "Query", "props": {"k": "v"}},
            {"id": "n2", "label": "Node 2", "type": "Finding", "props": {}},
        ],
        edge_rows=[
            {"source": "n1", "target": "n2", "type": "REL"},
            {"source": "n1", "target": "n3", "type": "REL"},
        ],
    )

    async def override_get_valkey():
        return dummy_valkey

    async def override_get_job_store():
        return store

    async def override_get_worker():
        return worker

    async def override_get_driver():
        return driver

    app.dependency_overrides[get_valkey] = override_get_valkey
    app.dependency_overrides[get_job_store] = override_get_job_store
    app.dependency_overrides[get_worker] = override_get_worker
    app.dependency_overrides[get_driver] = override_get_driver

    return TestClient(app)


def test_api_smoke_jobs_and_health() -> None:
    client = _make_app_with_overrides()

    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["service"] == "Axiom API"

    health = client.get("/health")
    assert health.status_code == 200
    assert "status" in health.json()

    settings = client.get("/settings")
    assert settings.status_code == 200
    data = settings.json()
    assert isinstance(data, dict)
    assert "axiom_axiomatizer_enabled" in data
    assert "axiom_breadth" in data
    assert "axiom_council_enabled" in data
    assert "axiom_council_size" in data

    resp = client.post("/jobs", json={"question": "What is Axiom?"})
    assert resp.status_code == 202
    job = resp.json()
    assert job["status"] == JobStatus.QUEUED.value

    job_id = job["id"]

    list_resp = client.get("/jobs")
    assert list_resp.status_code == 200
    jobs = list_resp.json()
    assert isinstance(jobs, list)
    assert any(item["id"] == job_id for item in jobs)

    get_resp = client.get(f"/jobs/{job_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == job_id

    with client.stream("GET", f"/jobs/{job_id}/stream") as stream_resp:
        assert stream_resp.status_code == 200
        assert stream_resp.headers["content-type"].startswith("text/event-stream")

def test_api_smoke_models_route() -> None:
    client = _make_app_with_overrides()

    resp = client.get("/models")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "models" in data
    assert isinstance(data["models"], list)



def test_api_smoke_graph_route() -> None:
    client = _make_app_with_overrides()

    resp = client.get("/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert [n["id"] for n in data["nodes"]] == ["n1", "n2"]
    assert data["links"] == [{"source": "n1", "target": "n2", "type": "REL"}]
