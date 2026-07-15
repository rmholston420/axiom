import pytest

from apps.axiomatizer.routers.axiomatizer import _extract_json_object


@pytest.mark.unit
def test_extract_json_object_from_plain_json():
    raw = '{"statement":"A","justification":"B","confidence":0.7}'
    data = _extract_json_object(raw)
    assert data["statement"] == "A"
    assert data["confidence"] == 0.7


@pytest.mark.unit
def test_extract_json_object_from_fenced_json():
    raw = '```json\n{"approved": true, "reason": "ok"}\n```'
    data = _extract_json_object(raw)
    assert data["approved"] is True
    assert data["reason"] == "ok"


@pytest.mark.unit
def test_extract_json_object_from_embedded_json():
    raw = 'prefix {"approved": false, "reason": "bad"} suffix'
    data = _extract_json_object(raw)
    assert data["approved"] is False
    assert data["reason"] == "bad"
