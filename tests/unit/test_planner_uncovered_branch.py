import pytest

from packages.axiom_research.planner import Planner, SubQuery


class DummyProvider:
    async def generate(self, *args, **kwargs):
        return "not json at all\n- first\n- second\n- third"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_plan_fallback_to_lines_when_json_parse_fails():
    planner = Planner(DummyProvider())

    plan = await planner.plan("question", breadth=2)

    assert plan == [
        SubQuery(text="not json at all", depth=0),
        SubQuery(text="first", depth=0),
    ]
