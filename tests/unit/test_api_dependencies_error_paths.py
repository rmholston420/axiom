import pytest
from fastapi import FastAPI

from apps.api.dependencies import lifespan


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lifespan_yields_app_and_runs_startup_and_shutdown(caplog):
    app = FastAPI()

    async with lifespan(app) as yielded_app:
        assert yielded_app is app

    messages = [rec.getMessage() for rec in caplog.records]
    assert any("Axiom API startup complete" in m for m in messages)
    assert any("Axiom API shutdown complete" in m for m in messages)
