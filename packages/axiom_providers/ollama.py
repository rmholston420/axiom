"""Ollama provider — thin async wrapper around the Ollama HTTP API."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from axiom_core.settings import settings


class OllamaProvider:
    """Async client for the local Ollama instance."""

    def __init__(self) -> None:
        self._base = settings.axiom_ollama_base_url.rstrip("/")

    async def generate(self, *, model: str, prompt: str, system: str = "") -> str:
        """Call Ollama chat endpoint (non-streaming) and return assistant text.

        All parameters are keyword-only so call sites and test mocks align.
        """
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

    async def generate_stream(
        self,
        *,
        model: str,
        prompt: str,
        system: str = "",
    ) -> AsyncIterator[str]:
        """Stream generation tokens from Ollama, yielding each text delta.

        Ollama's /api/chat endpoint with ``stream: true`` emits one JSON
        object per line.  Each object has the shape::

            {"message": {"content": "<delta>"}, "done": false}

        The final object has ``done: true`` and may carry usage stats.
        We yield only the non-empty ``content`` deltas.
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
        }

        # httpx streaming: use a long timeout because generation can be slow.
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
            async with client.stream(
                "POST", f"{self._base}/api/chat", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        import json
                        chunk = json.loads(line)
                    except Exception:  # noqa: BLE001
                        continue
                    delta = chunk.get("message", {}).get("content", "")
                    if delta:
                        yield delta
                    if chunk.get("done"):
                        break

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
