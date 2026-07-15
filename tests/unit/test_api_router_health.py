import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routers import health as health_router
from axiom_core.enums import ServiceName
from axiom_core.models import ServiceStatus


@pytest.mark.unit
def test_root_route_returns_service_metadata():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "Axiom API"
    assert body["version"] == "0.6.0"


@pytest.mark.unit
def test_health_route_returns_healthy_when_all_checks_pass(monkeypatch):
    async def ok_ollama():
        return ServiceStatus(name=ServiceName.OLLAMA, ok=True, detail="")

    async def ok_searxng():
        return ServiceStatus(name=ServiceName.SEARXNG, ok=True, detail="")

    async def ok_neo4j():
        return ServiceStatus(name=ServiceName.NEO4J, ok=True, detail="")

    async def ok_valkey():
        return ServiceStatus(name=ServiceName.VALKEY, ok=True, detail="")

    monkeypatch.setattr(health_router, "_check_ollama", ok_ollama)
    monkeypatch.setattr(health_router, "_check_searxng", ok_searxng)
    monkeypatch.setattr(health_router, "_check_neo4j", ok_neo4j)
    monkeypatch.setattr(health_router, "_check_valkey", ok_valkey)

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert [svc["name"] for svc in body["services"]] == ["ollama", "searxng", "neo4j", "valkey"]
    assert all(svc["ok"] is True for svc in body["services"])


@pytest.mark.unit
def test_health_route_returns_degraded_when_any_check_fails(monkeypatch):
    async def ok_ollama():
        return ServiceStatus(name=ServiceName.OLLAMA, ok=True, detail="")

    async def bad_searxng():
        return ServiceStatus(name=ServiceName.SEARXNG, ok=False, detail="boom")

    async def ok_neo4j():
        return ServiceStatus(name=ServiceName.NEO4J, ok=True, detail="")

    async def ok_valkey():
        return ServiceStatus(name=ServiceName.VALKEY, ok=True, detail="")

    monkeypatch.setattr(health_router, "_check_ollama", ok_ollama)
    monkeypatch.setattr(health_router, "_check_searxng", bad_searxng)
    monkeypatch.setattr(health_router, "_check_neo4j", ok_neo4j)
    monkeypatch.setattr(health_router, "_check_valkey", ok_valkey)

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert len(body["services"]) == 4
    assert body["services"][1]["name"] == "searxng"
    assert body["services"][1]["ok"] is False
    assert body["services"][1]["detail"] == "boom"
