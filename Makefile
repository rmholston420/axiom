PYTHON := python3
VENV_DIR := .venv
VENV_BIN := $(VENV_DIR)/bin
PORT ?= 7200

.PHONY: venv install api api-dev api-stop api-restart health lint test

install-packages:
	. $(VENV_BIN)/activate && \
		pip install -e packages/axiom_contracts && \
		pip install -e packages/axiom_core && \
		pip install -e packages/axiom_graph && \
		pip install -e packages/axiom_providers && \
		pip install -e packages/axiom_research


venv:
	$(PYTHON) -m venv $(VENV_DIR)
	. $(VENV_BIN)/activate && \
		python -m pip install --upgrade pip wheel setuptools && \
		python -m pip install \
			fastapi \
			"uvicorn[standard]" \
			neo4j \
			httpx \
			redis \
			pydantic \
			pydantic-settings \
			pytest \
			pytest-asyncio \
			ruff

install: venv

api-stop:
	-pkill -f 'python -m uvicorn apps.api.main:app' || true
	-pkill -f 'uvicorn apps.api.main:app' || true

api:
	. $(VENV_BIN)/activate && \
	python -m uvicorn apps.api.main:app --host 0.0.0.0 --port $(PORT)

api-dev:
	. $(VENV_BIN)/activate && \
	python -m uvicorn apps.api.main:app --host 0.0.0.0 --port $(PORT) --reload

api-restart: api-stop
	@sleep 1
	@$(MAKE) api

health:
	curl -sS http://localhost:$(PORT)/health | python3 -m json.tool

lint:
	. $(VENV_BIN)/activate && \
	python -m ruff check apps packages

test:
	. $(VENV_BIN)/activate && \
	pytest
