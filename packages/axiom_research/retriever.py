"""Retriever — fetches and extracts web evidence for a sub-query."""

from __future__ import annotations

from axiom_providers.searxng import SearchResult, SearxngProvider


class Retriever:
    def __init__(self, searxng: SearxngProvider) -> None:
        self._searxng = searxng

    async def retrieve(self, sub_query: str) -> list[SearchResult]:
        """Return search results for *sub_query*."""
        return await self._searxng.search(sub_query)
