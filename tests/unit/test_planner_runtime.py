import pytest

from packages.axiom_research import planner as planner_module
from packages.axiom_research.planner import Planner


class DummyOllama:
    def __init__(self, raw_response):
        self.raw_response = raw_response
        self.calls = []

    async def generate(self, *, model, prompt, system):
        self.calls.append({"model": model, "prompt": prompt, "system": system})
        return self.raw_response


@pytest.mark.unit
def test_planner_constructor_wires_provider():
    ollama = DummyOllama('["one"]')
    planner = Planner(ollama)

    assert planner._ollama is ollama


@pytest.mark.unit
@pytest.mark.asyncio
async def test_plan_uses_explicit_breadth_and_truncates_results(monkeypatch):
    ollama = DummyOllama('["one", "two", "three"]')

    class DummySettings:
        axiom_model_planner = "axiom-plan"
        axiom_breadth = 99

    monkeypatch.setattr(planner_module, "settings", DummySettings())

    planner = Planner(ollama)
    result = await planner.plan("Explain Axiom", breadth=2)

    assert [sq.text for sq in result] == ["one", "two"]
    assert all(sq.depth == 0 for sq in result)

    assert len(ollama.calls) == 1
    call = ollama.calls[0]
    assert call["model"] == "axiom-plan"
    assert call["system"] == planner_module._PLAN_SYSTEM
    assert "Generate exactly 2 search sub-queries" in call["prompt"]
    assert "Question: Explain Axiom" in call["prompt"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_plan_uses_settings_breadth_when_not_provided(monkeypatch):
    ollama = DummyOllama('["one", "two", "three"]')

    class DummySettings:
        axiom_model_planner = "axiom-plan"
        axiom_breadth = 2

    monkeypatch.setattr(planner_module, "settings", DummySettings())

    planner = Planner(ollama)
    result = await planner.plan("Explain Axiom")

    assert [sq.text for sq in result] == ["one", "two"]

    assert len(ollama.calls) == 1
    call = ollama.calls[0]
    assert "Generate exactly 2 search sub-queries" in call["prompt"]
