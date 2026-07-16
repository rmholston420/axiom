.PHONY: smoke unit test-all

smoke:
	pytest tests/integration/test_api_smoke.py

unit:
	pytest tests/unit

test-all:
	pytest tests/integration/test_api_smoke.py
	pytest tests/unit
