"""Shared Pydantic models."""

from pydantic import BaseModel

from .enums import ServiceName


class ServiceStatus(BaseModel):
    name: ServiceName
    ok: bool
    detail: str = ""


class HealthResponse(BaseModel):
    status: str  # "healthy" | "degraded"
    services: list[ServiceStatus]
    version: str = "0.1.0"
