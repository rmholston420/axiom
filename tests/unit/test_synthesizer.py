import pytest

from packages.axiom_research import synthesizer as synthesizer_module
from packages.axiom_research.models import RawFinding
from packages.axiom_research.synthesizer import Synthesizer


class DummyOllama:
    def __init__(self):
        self.calls = []

    async def generate(self, *, model, prompt, system):
        self.calls.append({"model": model, "prompt": prompt, "system": system})
        return "# Final Report"


class DummySearchResult:
    def __init__(self, url, title, snippet):
        self.url = url
        self.title = title
        self.snippet = snippet


@pytest.mark.unit
def test_synthesizer_constructor_wires_provider():
    ollama = DummyOllama()
    synth = Synthesizer(ollama)

    assert synth._ollama is ollama


@pytest.mark.unit
@pytest.mark.asyncio
async def test_synthesize_builds_prompt_and_calls_ollama(monkeypatch):
    ollama = DummyOllama()

    class DummySettings:
        axiom_model_synthesizer = "axiom-synth"

    monkeypatch.setattr(synthesizer_module, "settings", DummySettings())

    synth = Synthesizer(ollama)
    findings = [
        RawFinding(
            sub_query="History",
            results=[
                DummySearchResult(
                    url="https://example.com/history",
                    title="History Source",
                    snippet="A history snippet.",
                )
            ],
            summary="History summary",
        ),
        RawFinding(
            sub_query="Impact",
            results=[
                DummySearchResult(
                    url="https://example.com/impact",
                    title="Impact Source",
                    snippet="An impact snippet.",
                )
            ],
            summary="Impact summary",
        ),
    ]

    report = await synth.synthesize("What is Axiom?", findings)

    assert report == "# Final Report"
    assert len(ollama.calls) == 1
    call = ollama.calls[0]

    assert call["model"] == "axiom-synth"
    assert call["system"] == synthesizer_module._SYNTH_SYSTEM

    prompt = call["prompt"]
    assert "Research question: What is Axiom?" in prompt
    assert "Findings and evidence:" in prompt
    assert "### Finding 1: History" in prompt
    assert "History summary" in prompt
    assert "[1] History Source" in prompt
    assert "URL: https://example.com/history" in prompt
    assert "Snippet: A history snippet." in prompt
    assert "### Finding 2: Impact" in prompt
    assert "Impact summary" in prompt
    assert "[2] Impact Source" in prompt
    assert "URL: https://example.com/impact" in prompt
    assert "Snippet: An impact snippet." in prompt
    assert "Cite every non-trivial factual claim with inline numeric citations." in prompt
    assert "End with a '## Sources' section" in prompt


@pytest.mark.unit
@pytest.mark.asyncio
async def test_synthesize_handles_empty_findings(monkeypatch):
    ollama = DummyOllama()

    class DummySettings:
        axiom_model_synthesizer = "axiom-synth"

    monkeypatch.setattr(synthesizer_module, "settings", DummySettings())

    synth = Synthesizer(ollama)
    report = await synth.synthesize("What is Axiom?", [])

    assert report == "# Final Report"
    assert len(ollama.calls) == 1
    prompt = ollama.calls[0]["prompt"]
    assert "No findings were gathered." in prompt
