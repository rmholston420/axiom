import pytest

from axiom_providers.searxng import SearchResult
from packages.axiom_research.retriever import Retriever


class DummySearxng:
    def __init__(self, results):
        self.results = results
        self.calls = []

    async def search(self, query):
        self.calls.append(query)
        return self.results


@pytest.mark.unit
def test_retriever_constructor_wires_provider():
    provider = DummySearxng(results=[])
    retriever = Retriever(provider)

    assert retriever._searxng is provider


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_delegates_to_search_provider():
    results = [
        SearchResult(url="https://example.com/1", title="One", snippet="Snippet one"),
        SearchResult(url="https://example.com/2", title="Two", snippet="Snippet two"),
    ]
    provider = DummySearxng(results=results)
    retriever = Retriever(provider)

    returned = await retriever.retrieve("axiom research")

    assert returned == results
    assert provider.calls == ["axiom research"]
