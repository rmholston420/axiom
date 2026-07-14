.PHONY: install dev lint test compose

install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install poetry
	.venv/bin/poetry install

dev:
	.venv/bin/uvicorn apps.api.main:app --reload --port 7200

lint:
	.venv/bin/ruff check packages/ apps/api/

test:
	.venv/bin/pytest tests/

compose:
	docker compose up -d
