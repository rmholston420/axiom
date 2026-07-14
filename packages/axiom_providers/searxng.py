"""SearXNG provider — async search adapter."""
from __future__ import annotations

import httpx
from axiom_core.settings import settings


class SearchResult:
    __slots__ = ("title", "url", "snippet")

    def __init__(self, title: str, url: str, snippet: str) -> None:
        self.title = title
        self.url = url
        self.snippet = snippet

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SearchResult title={self.title!r}>"


class SearxngProvider:
    """Async client for the local SearXNG instance."""

    def __init__(self) -> None:
        self._base = settings.axiom_searxng_url.rstrip("/")

    async def search(
        self,
        query: str,
        num_results: int | None = None,
    ) -> list[SearchResult]:
        """Run a web search and return up to *num_results* results."""
        limit = num_results or settings.axiom_max_results_per_query
        params = {
            "q": query,
            "format": "json",
            "language": "en",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self._base}/search", params=params)
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("results", [])[:limit]:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                )
            )
        return results
