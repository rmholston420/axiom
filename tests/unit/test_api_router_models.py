import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.routers import models as models_router
from apps.api.routers.models import router


class DummyResponse:
    def __init__(self, payload, status_error=None):
        self._payload = payload
        self._status_error = status_error

    def raise_for_status(self):
        if self._status_error:
            raise self._status_error

    def json(self):
        return self._payload


class DummyAsyncClient:
    def __init__(self, response=None, error=None, *args, **kwargs):
        self.response = response
        self.error = error
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url):
        self.calls.append(url)
        if self.error:
            raise self.error
        return self.response


def make_app():
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.mark.unit
def test_list_models_returns_shaped_models(monkeypatch):
    response = DummyResponse(
        {
            "models": [
                {"name": "llama3", "size": 123, "modified_at": "2026-07-15T12:00:00Z"},
                {"name": "mistral", "size": 456, "modified_at": "2026-07-14T12:00:00Z"},
            ]
        }
    )

    monkeypatch.setattr(
        models_router.httpx,
        "AsyncClient",
        lambda *a, **k: DummyAsyncClient(response=response, *a, **k),
    )

    client = TestClient(make_app())
    result = client.get("/models")

    assert result.status_code == 200
    assert result.json() == {
        "models": [
            {"name": "llama3", "size": 123, "modified_at": "2026-07-15T12:00:00Z"},
            {"name": "mistral", "size": 456, "modified_at": "2026-07-14T12:00:00Z"},
        ]
    }


@pytest.mark.unit
def test_list_models_handles_missing_optional_fields(monkeypatch):
    response = DummyResponse(
        {
            "models": [
                {"name": "llama3"},
            ]
        }
    )

    monkeypatch.setattr(
        models_router.httpx,
        "AsyncClient",
        lambda *a, **k: DummyAsyncClient(response=response, *a, **k),
    )

    client = TestClient(make_app())
    result = client.get("/models")

    assert result.status_code == 200
    assert result.json() == {
        "models": [
            {"name": "llama3", "size": None, "modified_at": None},
        ]
    }


@pytest.mark.unit
def test_list_models_returns_empty_when_upstream_has_no_models(monkeypatch):
    response = DummyResponse({"models": []})

    monkeypatch.setattr(
        models_router.httpx,
        "AsyncClient",
        lambda *a, **k: DummyAsyncClient(response=response, *a, **k),
    )

    client = TestClient(make_app())
    result = client.get("/models")

    assert result.status_code == 200
    assert result.json() == {"models": []}


@pytest.mark.unit
def test_list_models_returns_empty_on_request_error(monkeypatch):
    monkeypatch.setattr(
        models_router.httpx,
        "AsyncClient",
        lambda *a, **k: DummyAsyncClient(error=httpx.ConnectError("ollama unavailable"), *a, **k),
    )

    client = TestClient(make_app())
    result = client.get("/models")

    assert result.status_code == 200
    assert result.json() == {"models": []}


@pytest.mark.unit
def test_list_models_returns_empty_on_http_status_error(monkeypatch):
    request = httpx.Request("GET", "http://ollama/api/tags")
    response_obj = httpx.Response(500, request=request)
    response = DummyResponse(
        payload={"models": [{"name": "ignored"}]},
        status_error=httpx.HTTPStatusError("boom", request=request, response=response_obj),
    )

    monkeypatch.setattr(
        models_router.httpx,
        "AsyncClient",
        lambda *a, **k: DummyAsyncClient(response=response, *a, **k),
    )

    client = TestClient(make_app())
    result = client.get("/models")

    assert result.status_code == 200
    assert result.json() == {"models": []}
