"""Settings endpoints — read and patch runtime config."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from axiom_core.settings import settings

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    axiom_breadth: int
    axiom_depth: int
    axiom_max_results_per_query: int
    axiom_council_size: int
    axiom_council_enabled: bool
    axiom_axiomatizer_enabled: bool
    axiom_model_planner: str
    axiom_model_synthesizer: str
    axiom_model_code: str
    axiom_model_critic: str
    axiom_model_chairman: str
    axiom_model_axiomatizer: str


class SettingsPatch(BaseModel):
    axiom_breadth: int | None = None
    axiom_depth: int | None = None
    axiom_max_results_per_query: int | None = None
    axiom_council_size: int | None = None
    axiom_council_enabled: bool | None = None
    axiom_axiomatizer_enabled: bool | None = None
    axiom_model_planner: str | None = None
    axiom_model_synthesizer: str | None = None
    axiom_model_code: str | None = None
    axiom_model_critic: str | None = None
    axiom_model_chairman: str | None = None
    axiom_model_axiomatizer: str | None = None


@router.get("", response_model=SettingsResponse)
async def get_settings():
    """Return current runtime settings."""
    return SettingsResponse(
        axiom_breadth=settings.axiom_breadth,
        axiom_depth=settings.axiom_depth,
        axiom_max_results_per_query=settings.axiom_max_results_per_query,
        axiom_council_size=settings.axiom_council_size,
        axiom_council_enabled=settings.axiom_council_enabled,
        axiom_axiomatizer_enabled=settings.axiom_axiomatizer_enabled,
        axiom_model_planner=settings.axiom_model_planner,
        axiom_model_synthesizer=settings.axiom_model_synthesizer,
        axiom_model_code=settings.axiom_model_code,
        axiom_model_critic=settings.axiom_model_critic,
        axiom_model_chairman=settings.axiom_model_chairman,
        axiom_model_axiomatizer=settings.axiom_model_axiomatizer,
    )


@router.patch("", response_model=SettingsResponse)
async def patch_settings(body: SettingsPatch):
    """Mutate the in-process settings singleton at runtime.

    NOTE: changes are in-memory only and reset on restart.
    Write to .env for persistence.
    """
    updates: dict[str, Any] = body.model_dump(exclude_none=True)
    for key, value in updates.items():
        if hasattr(settings, key):
            object.__setattr__(settings, key, value)
    return await get_settings()
