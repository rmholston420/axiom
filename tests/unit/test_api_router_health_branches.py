import httpx
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routers import health as health_router
from axiom_core.enums import ServiceName


class DummyHTTPResponse:
    def __init__(self, status_code):
        self.status_code = status_code


class DummyNeo4jDriver:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.closed = False
        self.verified = False

    async def verify_connectivity(self):
        self.verified = True
        if self.should_fail:
            raise RuntimeError("neo4j down")

    async def close(self):
        self.closed = True


class DummyRedisClient:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.closed = False
        self.pinged = False

    async def ping(self):
        self.pinged = True
        if self.should_fail:
            raise RuntimeError("valkey down")

    async def aclose(self):
        self.closed = True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_ollama_success(monkeypatch):
    async def fake_get(self, url):
        return DummyHTTPResponse(200)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    status = await health_router._check_ollama()

    assert status.name == ServiceName.OLLAMA
    assert status.ok is True
    assert status.detail == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_ollama_exception(monkeypatch):
    async def fake_get(self, url):
        raise RuntimeError("ollama down")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    status = await health_router._check_ollama()

    assert status.name == ServiceName.OLLAMA
    assert status.ok is False
    assert "ollama down" in status.detail


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_searxng_non_200(monkeypatch):
    async def fake_get(self, url):
        return DummyHTTPResponse(503)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    status = await health_router._check_searxng()

    assert status.name == ServiceName.SEARXNG
    assert status.ok is False
    assert status.detail == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_neo4j_success(monkeypatch):
    driver = DummyNeo4jDriver()
    monkeypatch.setattr(health_router.AsyncGraphDatabase, "driver", lambda *a, **k: driver)

    status = await health_router._check_neo4j()

    assert status.name == ServiceName.NEO4J
    assert status.ok is True
    assert driver.verified is True
    assert driver.closed is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_neo4j_exception(monkeypatch):
    driver = DummyNeo4jDriver(should_fail=True)
    monkeypatch.setattr(health_router.AsyncGraphDatabase, "driver", lambda *a, **k: driver)

    status = await health_router._check_neo4j()

    assert status.name == ServiceName.NEO4J
    assert status.ok is False
    assert "neo4j down" in status.detail


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_valkey_success(monkeypatch):
    client = DummyRedisClient()
    monkeypatch.setattr(health_router.Redis, "from_url", lambda *a, **k: client)

    status = await health_router._check_valkey()

    assert status.name == ServiceName.VALKEY
    assert status.ok is True
    assert client.pinged is True
    assert client.closed is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_valkey_exception(monkeypatch):
    client = DummyRedisClient(should_fail=True)
    monkeypatch.setattr(health_router.Redis, "from_url", lambda *a, **k: client)

    status = await health_router._check_valkey()

    assert status.name == ServiceName.VALKEY
    assert status.ok is False
    assert "valkey down" in status.detail


@pytest.mark.unit
def test_health_route_marks_timeout_as_degraded(monkeypatch):
    async def ok_ollama():
        return health_router.ServiceStatus(name=ServiceName.OLLAMA, ok=True)

    async def slow_searxng():
        raise TimeoutError

    async def ok_neo4j():
        return health_router.ServiceStatus(name=ServiceName.NEO4J, ok=True)

    async def ok_valkey():
        return health_router.ServiceStatus(name=ServiceName.VALKEY, ok=True)

    monkeypatch.setattr(health_router, "_check_ollama", ok_ollama)
    monkeypatch.setattr(health_router, "_check_searxng", slow_searxng)
    monkeypatch.setattr(health_router, "_check_neo4j", ok_neo4j)
    monkeypatch.setattr(health_router, "_check_valkey", ok_valkey)

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["services"][1]["name"] == "searxng"
    assert payload["services"][1]["ok"] is False
    assert payload["services"][1]["detail"] == "timeout"


@pytest.mark.unit
def test_health_route_marks_unexpected_exception_as_degraded(monkeypatch):
    async def boom_ollama():
        raise RuntimeError("unexpected boom")

    async def ok_searxng():
        return health_router.ServiceStatus(name=ServiceName.SEARXNG, ok=True)

    async def ok_neo4j():
        return health_router.ServiceStatus(name=ServiceName.NEO4J, ok=True)

    async def ok_valkey():
        return health_router.ServiceStatus(name=ServiceName.VALKEY, ok=True)

    monkeypatch.setattr(health_router, "_check_ollama", boom_ollama)
    monkeypatch.setattr(health_router, "_check_searxng", ok_searxng)
    monkeypatch.setattr(health_router, "_check_neo4j", ok_neo4j)
    monkeypatch.setattr(health_router, "_check_valkey", ok_valkey)

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["services"][0]["name"] == "ollama"
    assert payload["services"][0]["ok"] is False
    assert "unexpected boom" in payload["services"][0]["detail"]
