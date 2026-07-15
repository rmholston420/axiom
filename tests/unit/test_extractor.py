import types

import pytest

from axiom_providers.searxng import SearchResult
from packages.axiom_research import extractor as extractor_module
from packages.axiom_research.extractor import Extractor


class DummyOllama:
    def __init__(self):
        self.calls = []

    async def generate(self, *, model, prompt, system):
        self.calls.append({"model": model, "prompt": prompt, "system": system})
        return "generated summary"


def make_result(title, snippet):
    return SearchResult(url="https://example.com", title=title, snippet=snippet)


@pytest.mark.unit
def test_extractor_constructor_wires_provider():
    ollama = DummyOllama()
    ext = Extractor(ollama)

    assert ext._ollama is ollama


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_returns_fixed_message_on_empty_results():
    ollama = DummyOllama()
    ext = Extractor(ollama)

    summary = await ext.extract("What is Axiom?", results=[])

    assert summary == "No search results found for this sub-query."
    assert ollama.calls == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_builds_snippets_and_calls_ollama(monkeypatch):
    ollama = DummyOllama()

    # Use a known model value so we can assert it; override settings.
    class DummySettings:
        axiom_model_synthesizer = "axiom-synth"

    monkeypatch.setattr(extractor_module, "settings", DummySettings())

    ext = Extractor(ollama)
    results = [
        make_result("Title One", "Snippet one."),
        make_result("Title Two", "Snippet two."),
    ]

    summary = await ext.extract("What is Axiom?", results=results)

    assert summary == "generated summary"
    assert len(ollama.calls) == 1
    call = ollama.calls[0]

    assert call["model"] == "axiom-synth"
    assert call["system"] == extractor_module._EXTRACT_SYSTEM

    prompt = call["prompt"]
    assert "Sub-query: What is Axiom?" in prompt
    assert "Search results:" in prompt
    assert "[1] Title One" in prompt
    assert "Snippet one." in prompt
    assert "[2] Title Two" in prompt
    assert "Snippet two." in prompt
