import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.dependencies import get_driver
from apps.api.routers.graph import (
    _load_edges,
    _load_nodes,
    router,
)


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


def make_app(driver):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_driver] = lambda: driver
    return app


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_nodes_skips_null_ids_and_builds_models():
    rows = [
        {"id": "n1", "label": "Node 1", "type": "Query", "props": {"a": 1}},
        {"id": None, "label": "Bad", "type": "Query", "props": {"b": 2}},
        {"id": "n2", "label": "Node 2", "type": "Axiom", "props": {}},
    ]
    driver = DummyDriver(node_rows=rows)

    nodes = await _load_nodes(driver)

    assert [n.id for n in nodes] == ["n1", "n2"]
    assert nodes[0].label == "Node 1"
    assert nodes[0].type == "Query"
    assert nodes[0].properties == {"a": 1}
    assert nodes[1].type == "Axiom"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_edges_skips_null_endpoints():
    rows = [
        {"source": "n1", "target": "n2", "type": "REL"},
        {"source": None, "target": "n2", "type": "REL"},
        {"source": "n1", "target": None, "type": "REL"},
    ]
    driver = DummyDriver(edge_rows=rows)

    edges = await _load_edges(driver)

    assert len(edges) == 1
    assert edges[0].source == "n1"
    assert edges[0].target == "n2"
    assert edges[0].type == "REL"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_edges_filters_to_allowed_node_ids():
    rows = [
        {"source": "n1", "target": "n2", "type": "REL"},
        {"source": "n1", "target": "n3", "type": "REL"},
        {"source": "n4", "target": "n2", "type": "REL"},
    ]
    driver = DummyDriver(edge_rows=rows)

    edges = await _load_edges(driver, allowed_node_ids={"n1", "n2"})

    assert len(edges) == 1
    assert edges[0].source == "n1"
    assert edges[0].target == "n2"


@pytest.mark.unit
def test_get_graph_returns_nodes_and_filtered_links():
    node_rows = [
        {"id": "n1", "label": "Node 1", "type": "Query", "props": {"k": "v"}},
        {"id": "n2", "label": "Node 2", "type": "Finding", "props": {}},
    ]
    edge_rows = [
        {"source": "n1", "target": "n2", "type": "REL"},
        {"source": "n1", "target": "n3", "type": "REL"},
    ]
    driver = DummyDriver(node_rows=node_rows, edge_rows=edge_rows)
    client = TestClient(make_app(driver))

    response = client.get("/graph")

    assert response.status_code == 200
    payload = response.json()
    assert [n["id"] for n in payload["nodes"]] == ["n1", "n2"]
    assert payload["links"] == [{"source": "n1", "target": "n2", "type": "REL"}]


@pytest.mark.unit
def test_get_nodes_returns_node_payload():
    node_rows = [
        {"id": "n1", "label": "Node 1", "type": "Source", "props": {"url": "x"}},
    ]
    driver = DummyDriver(node_rows=node_rows)
    client = TestClient(make_app(driver))

    response = client.get("/graph/nodes")

    assert response.status_code == 200
    assert response.json() == {
        "nodes": [{"id": "n1", "label": "Node 1", "type": "Source", "properties": {"url": "x"}}]
    }


@pytest.mark.unit
def test_get_edges_returns_filtered_edge_payload():
    node_rows = [
        {"id": "n1", "label": "Node 1", "type": "Query", "props": {}},
        {"id": "n2", "label": "Node 2", "type": "Axiom", "props": {}},
    ]
    edge_rows = [
        {"source": "n1", "target": "n2", "type": "SUPPORTS"},
        {"source": "n1", "target": "n3", "type": "SUPPORTS"},
    ]
    driver = DummyDriver(node_rows=node_rows, edge_rows=edge_rows)
    client = TestClient(make_app(driver))

    response = client.get("/graph/edges")

    assert response.status_code == 200
    assert response.json() == {"edges": [{"source": "n1", "target": "n2", "type": "SUPPORTS"}]}
