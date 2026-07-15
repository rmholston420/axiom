import pytest
from fastapi.testclient import TestClient

from apps.axiomatizer.main import app


@pytest.mark.unit
def test_app_metadata_is_set():
    assert app.title == "Axiom Axiomatizer"
    assert app.description == "Axiom — Local Research Workbench axiom proposal, evaluation, and storage service"
    assert app.version == "0.6.0"


@pytest.mark.unit
def test_root_route_returns_service_metadata():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "Axiom Axiomatizer",
        "version": "0.6.0",
    }


@pytest.mark.unit
def test_health_route_returns_healthy_service_status():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "axiom-axiomatizer",
    }


@pytest.mark.unit
def test_axiomatizer_router_paths_are_registered():
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/" in paths
    assert "/health" in paths
    assert "/axiomatizer" in paths
    assert "/axiomatizer/axioms" in paths
