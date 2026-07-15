import pytest
from fastapi import FastAPI

from apps.api import dependencies


class DummyDriver:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


class DummyValkey:
    def __init__(self):
        self.closed = False

    async def aclose(self):
        self.closed = True


class DummyWorker:
    def __init__(self, driver, valkey):
        self.driver = driver
        self.valkey = valkey
        self.stopped = False

    async def run_forever(self):
        return None

    def stop(self):
        self.stopped = True


class DummyTask:
    def __init__(self):
        self.cancelled = False
        self.awaited = False

    def cancel(self):
        self.cancelled = True

    def __await__(self):
        async def _inner():
            self.awaited = True
            raise asyncio.CancelledError
        return _inner().__await__()


class DummyJobStore:
    def __init__(self, valkey):
        self.valkey = valkey


import asyncio


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lifespan_sets_and_cleans_app_state(monkeypatch):
    driver = DummyDriver()
    valkey = DummyValkey()
    task = DummyTask()

    monkeypatch.setattr(dependencies.AsyncGraphDatabase, "driver", lambda *a, **k: driver)
    monkeypatch.setattr(dependencies, "ValkeyProvider", lambda: valkey)
    monkeypatch.setattr(dependencies, "QueueWorker", DummyWorker)
    monkeypatch.setattr(dependencies, "JobStore", DummyJobStore)
    monkeypatch.setattr(dependencies.asyncio, "create_task", lambda coro: task)

    app = FastAPI()

    async with dependencies.lifespan(app):
        assert app.state.driver is driver
        assert app.state.valkey is valkey
        assert isinstance(app.state.job_store, DummyJobStore)
        assert isinstance(app.state.worker, DummyWorker)

    assert app.state.worker.stopped is True
    assert task.cancelled is True
    assert task.awaited is True
    assert valkey.closed is True
    assert driver.closed is True
