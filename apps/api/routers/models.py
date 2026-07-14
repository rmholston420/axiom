"""Models endpoint — list available Ollama models."""
from __future__ import annotations

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from axiom_core.settings import settings

router = APIRouter(prefix="/models", tags=["models"])


class ModelInfo(BaseModel):
    name: str
    size: int | None = None
    modified_at: str | None = None


class ModelsResponse(BaseModel):
    models: list[ModelInfo]


@router.get("", response_model=ModelsResponse)
async def list_models():
    """Proxy Ollama /api/tags to list locally available models."""
    url = settings.axiom_ollama_base_url.rstrip("/") + "/api/tags"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            models = [
                ModelInfo(
                    name=m["name"],
                    size=m.get("size"),
                    modified_at=m.get("modified_at"),
                )
                for m in data.get("models", [])
            ]
    except Exception:  # noqa: BLE001
        models = []
    return ModelsResponse(models=models)
