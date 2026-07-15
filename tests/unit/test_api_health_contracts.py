import pytest

from axiom_core.enums import ServiceName
from axiom_core.models import HealthResponse, ServiceStatus


@pytest.mark.unit
def test_service_status_accepts_known_service_names():
    svc = ServiceStatus(name=ServiceName.OLLAMA, ok=True, detail="")
    assert svc.name == ServiceName.OLLAMA
    assert svc.ok is True


@pytest.mark.unit
def test_health_response_preserves_service_order():
    payload = HealthResponse(
        status="healthy",
        services=[
            ServiceStatus(name=ServiceName.OLLAMA, ok=True, detail=""),
            ServiceStatus(name=ServiceName.SEARXNG, ok=False, detail="down"),
            ServiceStatus(name=ServiceName.NEO4J, ok=True, detail=""),
        ],
        version="0.1.0",
    )
    names = [svc.name.value for svc in payload.services]
    assert names == ["ollama", "searxng", "neo4j"]
