"""Extractor — summarises raw search results for a sub-query via Ollama."""
from __future__ import annotations

from axiom_core.settings import settings
from axiom_providers.ollama import OllamaProvider
from axiom_providers.searxng import SearchResult

_EXTRACT_SYSTEM = (
    "You are a research assistant. Given a sub-query and a list of search result"
    " snippets, write a concise factual summary (3-5 sentences) that directly"
    " answers the sub-query. Do not speculate beyond the provided evidence."
)


class Extractor:
    def __init__(self, ollama: OllamaProvider) -> None:
        self._ollama = ollama

    async def extract(self, sub_query: str, results: list[SearchResult]) -> str:
        """Return a concise summary grounded in *results*."""
        if not results:
            return "No search results found for this sub-query."

        snippets = "\n".join(
            f"[{i + 1}] {r.title}\n{r.snippet}" for i, r in enumerate(results)
        )
        prompt = (
            f"Sub-query: {sub_query}\n\n"
            f"Search results:\n{snippets}\n\n"
            "Write a concise summary."
        )
        return await self._ollama.generate(
            model=settings.axiom_model_synthesizer,
            prompt=prompt,
            system=_EXTRACT_SYSTEM,
        )
