import pytest

from packages.axiom_research.planner import Planner


class DummyProvider:
    async def generate(self, *args, **kwargs):
        return "[]"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_plan_handles_non_list_json_by_falling_back_to_lines(monkeypatch):
    planner = Planner(DummyProvider())

    async def fake_generate(*args, **kwargs):
        return "not json\n- item one\n- item two"

    monkeypatch.setattr(planner._provider, "generate", fake_generate)

    plan = await planner.plan("question", breadth=2)
    assert len(plan.sub_queries) == 2
