from axiom_research.planner import _parse_json_list


def test_parse_json_list_from_clean_json():
    text = '["alpha", "beta", "gamma"]'
    assert _parse_json_list(text) == ["alpha", "beta", "gamma"]


def test_parse_json_list_from_markdown_fence():
    text = '```json\n["alpha", "beta"]\n```'
    assert _parse_json_list(text) == ["alpha", "beta"]


def test_parse_json_list_fallback_to_lines():
    text = "alpha\nbeta\ngamma"
    assert _parse_json_list(text) == ["alpha", "beta", "gamma"]
