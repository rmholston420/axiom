.PHONY: smoke unit test-all

smoke:
	pytest tests/integration/test_api_smoke.py -v

unit:
	pytest tests/unit -v

test-all:
	pytest tests/integration/test_api_smoke.py -v
	pytest tests/unit -v
