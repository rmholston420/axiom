import httpx
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routers import axiomatizer as axiomatizer_router


class DummyResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else {}
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "http://testserver/axiomatizer")
            response = httpx.Response(self.status_code, request=request, text=self.text)
            raise httpx.HTTPStatusError("upstream error", request=request, response=response)

    def json(self):
        return self._json_data


@pytest.mark.unit
def test_axiomatizer_proxy_success(monkeypatch):
    async def fake_post(self, url, json):
        return DummyResponse(200, {"axiom_id": "123", "statement": json["source_text"]})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(axiomatizer_router.settings, "axiom_axiomatizer_enabled", True)

    client = TestClient(app)
    response = client.post(
        "/axiomatizer",
        json={
            "source_text": "This is long enough text.",
            "context": "ctx",
            "label": "lbl",
        },
    )

    assert response.status_code == 200
    assert response.json()["axiom_id"] == "123"


@pytest.mark.unit
def test_axiomatizer_proxy_disabled(monkeypatch):
    monkeypatch.setattr(axiomatizer_router.settings, "axiom_axiomatizer_enabled", False)

    client = TestClient(app)
    response = client.post(
        "/axiomatizer",
        json={
            "source_text": "This is long enough text.",
            "context": "",
            "label": "",
        },
    )

    assert response.status_code == 503
    assert "Axiomatizer is disabled" in response.json()["detail"]


@pytest.mark.unit
def test_axiomatizer_proxy_connect_error(monkeypatch):
    async def fake_post(self, url, json):
        request = httpx.Request("POST", url)
        raise httpx.ConnectError("cannot connect", request=request)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(axiomatizer_router.settings, "axiom_axiomatizer_enabled", True)

    client = TestClient(app)
    response = client.post(
        "/axiomatizer",
        json={
            "source_text": "This is long enough text.",
            "context": "",
            "label": "",
        },
    )

    assert response.status_code == 503
    assert "not reachable" in response.json()["detail"]


@pytest.mark.unit
def test_axiomatizer_proxy_http_error(monkeypatch):
    async def fake_post(self, url, json):
        return DummyResponse(500, text="axiomatizer failed")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(axiomatizer_router.settings, "axiom_axiomatizer_enabled", True)

    client = TestClient(app)
    response = client.post(
        "/axiomatizer",
        json={
            "source_text": "This is long enough text.",
            "context": "",
            "label": "",
        },
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "axiomatizer failed"


@pytest.mark.unit
def test_list_axioms_success(monkeypatch):
    async def fake_get(self, url, params):
        return DummyResponse(200, [{"id": "a1"}, {"id": "a2"}])

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.setattr(axiomatizer_router.settings, "axiom_axiomatizer_enabled", True)

    client = TestClient(app)
    response = client.get("/axiomatizer/axioms?limit=2")

    assert response.status_code == 200
    assert response.json() == [{"id": "a1"}, {"id": "a2"}]


@pytest.mark.unit
def test_list_axioms_connect_error(monkeypatch):
    async def fake_get(self, url, params):
        request = httpx.Request("GET", url)
        raise httpx.ConnectError("cannot connect", request=request)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.setattr(axiomatizer_router.settings, "axiom_axiomatizer_enabled", True)

    client = TestClient(app)
    response = client.get("/axiomatizer/axioms?limit=2")

    assert response.status_code == 503
    assert "not reachable" in response.json()["detail"]


@pytest.mark.unit
def test_list_axioms_http_error(monkeypatch):
    async def fake_get(self, url, params):
        return DummyResponse(404, text="missing")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.setattr(axiomatizer_router.settings, "axiom_axiomatizer_enabled", True)

    client = TestClient(app)
    response = client.get("/axiomatizer/axioms?limit=2")

    assert response.status_code == 404
    assert response.json()["detail"] == "missing"
