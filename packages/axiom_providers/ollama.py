"""Ollama provider — thin async wrapper around the Ollama HTTP API."""

from __future__ import annotations

import httpx

from axiom_core.settings import settings


class OllamaProvider:
    """Async client for the local Ollama instance."""

    def __init__(self) -> None:
        self._base = settings.axiom_ollama_base_url.rstrip("/")

    async def generate(self, model: str, prompt: str, system: str = "") -> str:
        """Call Ollama native chat endpoint and return assistant text."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self._base}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]

    async def list_models(self) -> list[str]:
        """Return a list of locally available model names."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self._base}/api/tags")
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]

    async def healthcheck(self) -> dict:
        """Return model inventory for fast debugging."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self._base}/api/tags")
            resp.raise_for_status()
            return resp.json()
