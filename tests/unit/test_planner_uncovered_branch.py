import pytest

from packages.axiom_research.planner import Planner


class DummyProvider:
    async def generate(self, *args, **kwargs):
        # Force the non-JSON fallback path in the planner parser
        return "not json at all\n- first\n- second\n- third"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_plan_fallback_to_lines_when_json_parse_fails(monkeypatch):
    provider = DummyProvider()
    planner = Planner(provider)

    # Ensure breadth constrains the number of sub_queries even on fallback
    plan = await planner.plan("question", breadth=2)
    assert len(plan.sub_queries) == 2
