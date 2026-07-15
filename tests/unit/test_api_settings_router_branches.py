import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


@pytest.mark.unit
def test_settings_route_returns_known_public_fields():
    resp = client.get("/settings")
    assert resp.status_code == 200
    data = resp.json()

    # Match the actual key names used in the settings router
    assert "axiom_axiomatizer_enabled" in data
    assert isinstance(data["axiom_axiomatizer_enabled"], bool)
    assert "axiom_breadth" in data
    assert isinstance(data["axiom_breadth"], int)
    assert "axiom_graph_node_limit" in data
    assert isinstance(data["axiom_graph_node_limit"], int)
    assert "axiom_graph_edge_limit" in data
    assert isinstance(data["axiom_graph_edge_limit"], int)


@pytest.mark.unit
def test_settings_route_includes_council_configuration():
    resp = client.get("/settings")
    assert resp.status_code == 200
    data = resp.json()

    assert "axiom_council_enabled" in data
    assert isinstance(data["axiom_council_enabled"], bool)
    assert "axiom_council_size" in data
    assert isinstance(data["axiom_council_size"], int)
