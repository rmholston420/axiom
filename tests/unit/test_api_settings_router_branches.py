import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


@pytest.mark.unit
def test_settings_route_returns_public_settings():
    resp = client.get("/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "api_base_url" in data
    assert "axiomatizer_enabled" in data


@pytest.mark.unit
def test_settings_route_handles_unknown_field_access_gracefully():
    resp = client.get("/settings")
    data = resp.json()
    assert isinstance(data.get("axiomatizer_enabled"), bool)
