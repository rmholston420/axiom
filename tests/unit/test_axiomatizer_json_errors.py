import json
import pytest

from apps.axiomatizer.routers.axiomatizer import _extract_json_object


@pytest.mark.unit
def test_extract_json_object_raises_on_no_json():
    with pytest.raises(json.JSONDecodeError):
        _extract_json_object("this string has no json object")


@pytest.mark.unit
def test_extract_json_object_prefers_wrapped_object():
    raw = 'noise before {"approved": true, "reason": "wrapped"} trailing noise'
    data = _extract_json_object(raw)
    assert data["approved"] is True
    assert data["reason"] == "wrapped"
