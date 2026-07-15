import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError, TimeoutError

from apps.api.dependencies import get_job_store, get_worker
from apps.api.routers.jobs import router


class DummyWorker:
    def __init__(self, job_id="job-123"):
        self.job_id = job_id
        self.enqueue_calls = []

    async def enqueue(self, question):
        self.enqueue_calls.append(question)
        return self.job_id


class DummyStore:
    def __init__(self, jobs=None, get_error=None, list_error=None):
        self.jobs = jobs or {}
        self.get_error = get_error
        self.list_error = list_error
        self.get_calls = []
        self.list_calls = 0

    async def get(self, job_id):
        self.get_calls.append(job_id)
        if self.get_error:
            raise self.get_error
        return self.jobs.get(job_id)

    async def list_all(self):
        self.list_calls += 1
        if self.list_error:
            raise self.list_error
        return list(self.jobs.values())


def make_app(worker, store):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_worker] = lambda: worker
    app.dependency_overrides[get_job_store] = lambda: store
    return app


def sample_job(job_id="job-123", question="What is Axiom?", status="queued"):
    return {
        "id": job_id,
        "question": question,
        "status": status,
        "created_at": "2026-07-15T12:00:00Z",
        "updated_at": "2026-07-15T12:00:00Z",
        "report": "",
        "error": "",
    }


@pytest.mark.unit
def test_create_job_enqueues_and_returns_store_record():
    worker = DummyWorker(job_id="job-123")
    store = DummyStore(jobs={"job-123": sample_job()})
    client = TestClient(make_app(worker, store))

    response = client.post("/jobs", json={"question": "What is Axiom?"})

    assert response.status_code == 202
    assert response.json()["id"] == "job-123"
    assert response.json()["question"] == "What is Axiom?"
    assert worker.enqueue_calls == ["What is Axiom?"]
    assert store.get_calls == ["job-123"]


@pytest.mark.unit
def test_list_jobs_returns_jobs():
    store = DummyStore(
        jobs={
            "job-1": sample_job("job-1", "Q1", "queued"),
            "job-2": sample_job("job-2", "Q2", "done"),
        }
    )
    client = TestClient(make_app(DummyWorker(), store))

    response = client.get("/jobs")

    assert response.status_code == 200
    payload = response.json()
    assert [job["id"] for job in payload] == ["job-1", "job-2"]
    assert store.list_calls == 1


@pytest.mark.unit
def test_list_jobs_returns_empty_on_connection_error():
    store = DummyStore(list_error=ConnectionError("redis down"))
    client = TestClient(make_app(DummyWorker(), store))

    response = client.get("/jobs")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.unit
def test_list_jobs_returns_empty_on_timeout_error():
    store = DummyStore(list_error=TimeoutError("redis timeout"))
    client = TestClient(make_app(DummyWorker(), store))

    response = client.get("/jobs")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.unit
def test_get_job_returns_single_job():
    store = DummyStore(jobs={"job-9": sample_job("job-9", "Q9", "done")})
    client = TestClient(make_app(DummyWorker(), store))

    response = client.get("/jobs/job-9")

    assert response.status_code == 200
    assert response.json()["id"] == "job-9"
    assert store.get_calls == ["job-9"]


@pytest.mark.unit
def test_get_job_returns_404_when_missing():
    store = DummyStore(jobs={})
    client = TestClient(make_app(DummyWorker(), store))

    response = client.get("/jobs/missing-job")

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}
