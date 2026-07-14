"""Ollama provider — thin async wrapper around the Ollama HTTP API."""
from __future__ import annotations

import httpx
from axiom_core.settings import settings


class OllamaProvider:
    """Async client for the local Ollama instance."""

    def __init__(self) -> None:
        self._base = settings.axiom_ollama_base_url.rstrip("/")

    async def generate(self, model: str, prompt: str, system: str = "") -> str:
        """Call /api/generate and return the full response text."""
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self._base}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")

    async def list_models(self) -> list[str]:
        """Return a list of locally available model names."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self._base}/api/tags")
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
