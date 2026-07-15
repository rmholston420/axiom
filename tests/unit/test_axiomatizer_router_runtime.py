import types

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from apps.axiomatizer.routers import axiomatizer as ax_router
from apps.axiomatizer.routers.axiomatizer import router


class DummyOllama:
    def __init__(self, responses):
        self._responses = list(responses)

    async def generate(self, **kwargs):
        return self._responses.pop(0)


class DummySession:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.run_calls = []

    async def run(self, cypher, **kwargs):
        self.run_calls.append((cypher, kwargs))
        return DummyResult(self.rows)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


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


class DummyDriver:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.closed = False
        self.session_obj = DummySession(self.rows)

    def session(self):
        return self.session_obj

    async def close(self):
        self.closed = True


def make_app(with_driver=None):
    app = FastAPI()
    app.include_router(router)
    if with_driver is not None:
        app.state.driver = with_driver
    return app


@pytest.mark.unit
@pytest.mark.asyncio
async def test_propose_axiom_success():
    ollama = DummyOllama([
        '{"statement":"A implies B","justification":"because","confidence":0.75}'
    ])

    result = await ax_router._propose_axiom(ollama, "source text", "ctx")

    assert result == {
        "statement": "A implies B",
        "justification": "because",
        "confidence": 0.75,
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_propose_axiom_parse_failure_raises_http_502():
    ollama = DummyOllama(["not json at all"])

    with pytest.raises(ax_router.HTTPException) as excinfo:
        await ax_router._propose_axiom(ollama, "source text", "")

    assert excinfo.value.status_code == 502
    assert "Unparseable axiomatizer JSON" in excinfo.value.detail


@pytest.mark.unit
@pytest.mark.asyncio
async def test_evaluate_axiom_success():
    ollama = DummyOllama([
        '{"approved": false, "reason": "too vague"}'
    ])

    result = await ax_router._evaluate_axiom(ollama, "stmt", "justification")

    assert result == {"approved": False, "reason": "too vague"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_evaluate_axiom_parse_failure_defaults_to_approved():
    ollama = DummyOllama(["not json"])

    result = await ax_router._evaluate_axiom(ollama, "stmt", "justification")

    assert result["approved"] is True
    assert "defaulting to approved" in result["reason"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_driver_uses_app_state_driver():
    driver = DummyDriver()
    request = types.SimpleNamespace(app=types.SimpleNamespace(state=types.SimpleNamespace(driver=driver)))

    got_driver, should_close = await ax_router._get_driver(request)

    assert got_driver is driver
    assert should_close is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_driver_creates_standalone_driver(monkeypatch):
    driver = DummyDriver()
    monkeypatch.setattr(ax_router.AsyncGraphDatabase, "driver", lambda *a, **k: driver)
    request = types.SimpleNamespace(app=types.SimpleNamespace(state=types.SimpleNamespace()))

    got_driver, should_close = await ax_router._get_driver(request)

    assert got_driver is driver
    assert should_close is True


@pytest.mark.unit
def test_run_axiomatizer_disabled(monkeypatch):
    monkeypatch.setattr(ax_router.settings, "axiom_axiomatizer_enabled", False)
    client = TestClient(make_app())

    response = client.post("/axiomatizer", json={
        "source_text": "This is long enough text.",
        "context": "",
        "label": "",
    })

    assert response.status_code == 503
    assert "Axiomatizer is disabled" in response.json()["detail"]


@pytest.mark.unit
def test_run_axiomatizer_empty_statement_returns_502(monkeypatch):
    monkeypatch.setattr(ax_router.settings, "axiom_axiomatizer_enabled", True)
    monkeypatch.setattr(
        ax_router,
        "_propose_axiom",
        lambda *a, **k: _awaitable({"statement": "", "justification": "j", "confidence": 0.5}),
    )

    client = TestClient(make_app())

    response = client.post("/axiomatizer", json={
        "source_text": "This is long enough text.",
        "context": "",
        "label": "",
    })

    assert response.status_code == 502
    assert "empty statement" in response.json()["detail"]


@pytest.mark.unit
def test_run_axiomatizer_success_with_shared_driver(monkeypatch):
    monkeypatch.setattr(ax_router.settings, "axiom_axiomatizer_enabled", True)
    monkeypatch.setattr(ax_router, "OllamaProvider", lambda: object())
    monkeypatch.setattr(
        ax_router,
        "_propose_axiom",
        lambda *a, **k: _awaitable({"statement": "axiom statement", "justification": "because", "confidence": 0.9}),
    )
    monkeypatch.setattr(
        ax_router,
        "_evaluate_axiom",
        lambda *a, **k: _awaitable({"approved": True, "reason": "ok"}),
    )

    driver = DummyDriver()
    client = TestClient(make_app(with_driver=driver))

    response = client.post("/axiomatizer", json={
        "source_text": "This is long enough text.",
        "context": "ctx",
        "label": "",
    })

    assert response.status_code == 200
    payload = response.json()
    assert payload["statement"] == "axiom statement"
    assert payload["label"] == "axiom statement"
    assert payload["persisted"] is True
    assert driver.closed is False
    assert len(driver.session_obj.run_calls) == 1


@pytest.mark.unit
def test_run_axiomatizer_success_with_standalone_driver(monkeypatch):
    monkeypatch.setattr(ax_router.settings, "axiom_axiomatizer_enabled", True)
    monkeypatch.setattr(ax_router, "OllamaProvider", lambda: object())
    monkeypatch.setattr(
        ax_router,
        "_propose_axiom",
        lambda *a, **k: _awaitable({"statement": "standalone axiom", "justification": "because", "confidence": 0.7}),
    )
    monkeypatch.setattr(
        ax_router,
        "_evaluate_axiom",
        lambda *a, **k: _awaitable({"approved": False, "reason": "review"}),
    )

    driver = DummyDriver()
    monkeypatch.setattr(ax_router.AsyncGraphDatabase, "driver", lambda *a, **k: driver)

    client = TestClient(make_app())

    response = client.post("/axiomatizer", json={
        "source_text": "This is long enough text.",
        "context": "",
        "label": "custom label",
    })

    assert response.status_code == 200
    payload = response.json()
    assert payload["label"] == "custom label"
    assert payload["confidence"] == 0.7
    assert driver.closed is True
    assert len(driver.session_obj.run_calls) == 1


@pytest.mark.unit
def test_list_axioms_disabled(monkeypatch):
    monkeypatch.setattr(ax_router.settings, "axiom_axiomatizer_enabled", False)
    client = TestClient(make_app())

    response = client.get("/axiomatizer/axioms")

    assert response.status_code == 503
    assert "Axiomatizer is disabled" in response.json()["detail"]


@pytest.mark.unit
def test_list_axioms_returns_rows_and_closes_standalone_driver(monkeypatch):
    monkeypatch.setattr(ax_router.settings, "axiom_axiomatizer_enabled", True)
    rows = [
        {"a": {"id": "a1", "label": "First"}},
        {"a": {"id": "a2", "label": "Second"}},
    ]
    driver = DummyDriver(rows=rows)
    monkeypatch.setattr(ax_router.AsyncGraphDatabase, "driver", lambda *a, **k: driver)

    client = TestClient(make_app())

    response = client.get("/axiomatizer/axioms?limit=2")

    assert response.status_code == 200
    assert response.json() == [
        {"id": "a1", "label": "First"},
        {"id": "a2", "label": "Second"},
    ]
    assert driver.closed is True


def _awaitable(value):
    async def _coro():
        return value
    return _coro()
