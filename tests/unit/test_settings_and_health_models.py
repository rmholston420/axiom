import pytest

from axiom_core.enums import ServiceName
from axiom_core.models import HealthResponse, ServiceStatus
from axiom_core.settings import settings


@pytest.mark.unit
def test_settings_ports_are_ints():
    assert isinstance(settings.axiom_api_port, int)
    assert isinstance(settings.axiom_council_port, int)
    assert isinstance(settings.axiom_axiomatizer_port, int)
    assert isinstance(settings.axiom_web_port, int)


@pytest.mark.unit
def test_health_response_model_round_trip():
    payload = HealthResponse(
        status="healthy",
        services=[
            ServiceStatus(name=ServiceName.OLLAMA, ok=True, detail=""),
            ServiceStatus(name=ServiceName.NEO4J, ok=True, detail=""),
        ],
        version="0.1.0",
    )
    dumped = payload.model_dump()
    assert dumped["status"] == "healthy"
    assert len(dumped["services"]) == 2
    assert dumped["services"][0]["name"] == "ollama"
