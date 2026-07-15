import asyncio

import pytest
from fastapi import FastAPI

from apps.api.dependencies import lifespan


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lifespan_logs_and_continues_on_shutdown_error(caplog):
    app = FastAPI()

    async def failing_shutdown():
        raise RuntimeError("shutdown boom")

    app.state.on_shutdown = failing_shutdown  # type: ignore[attr-defined]

    async with lifespan(app):
        pass

    error_logs = [rec for rec in caplog.records if "shutdown boom" in rec.getMessage()]
    assert error_logs
