import httpx
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routers import council as council_router


class DummyResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else {}
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://testserver/council")
            response = httpx.Response(self.status_code, request=request, text=self.text)
            raise httpx.HTTPStatusError("upstream error", request=request, response=response)

    def json(self):
        return self._json_data


@pytest.mark.unit
def test_council_proxy_success(monkeypatch):
    async def fake_post(self, url, json):
        return DummyResponse(200, {"answer": "ok", "mode": json["mode"]})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    client = TestClient(app)
    response = client.post(
        "/council",
        json={
            "question": "What is the plan?",
            "context": "ctx",
            "council_size": 3,
            "mode": "parallel",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"answer": "ok", "mode": "parallel"}


@pytest.mark.unit
def test_council_proxy_disabled(monkeypatch):
    monkeypatch.setattr(council_router.settings, "axiom_council_enabled", False)

    client = TestClient(app)
    response = client.post(
        "/council",
        json={
            "question": "What is the plan?",
            "context": "",
            "council_size": 1,
            "mode": "sequential",
        },
    )

    assert response.status_code == 503
    assert "Council is disabled" in response.json()["detail"]


@pytest.mark.unit
def test_council_proxy_connect_error(monkeypatch):
    async def fake_post(self, url, json):
        request = httpx.Request("POST", url)
        raise httpx.ConnectError("cannot connect", request=request)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(council_router.settings, "axiom_council_enabled", True)

    client = TestClient(app)
    response = client.post(
        "/council",
        json={
            "question": "What is the plan?",
            "context": "",
            "council_size": 1,
            "mode": "sequential",
        },
    )

    assert response.status_code == 503
    assert "not reachable" in response.json()["detail"]


@pytest.mark.unit
def test_council_proxy_http_error(monkeypatch):
    async def fake_post(self, url, json):
        return DummyResponse(502, text="bad upstream")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(council_router.settings, "axiom_council_enabled", True)

    client = TestClient(app)
    response = client.post(
        "/council",
        json={
            "question": "What is the plan?",
            "context": "",
            "council_size": 1,
            "mode": "sequential",
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "bad upstream"
