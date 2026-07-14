PYTHON := python3
VENV_DIR := .venv
VENV_BIN := $(VENV_DIR)/bin
PORT ?= 7200
COUNCIL_PORT ?= 7201
AXIOMATIZER_PORT ?= 7202

.PHONY: venv install install-packages api api-dev api-stop api-restart health lint test \
        council council-dev council-stop council-restart council-health \
        axiomatizer axiomatizer-dev axiomatizer-stop axiomatizer-restart axiomatizer-health

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
		python -m pip install fastapi "uvicorn[standard]" httpx neo4j redis pydantic pydantic-settings pytest pytest-asyncio ruff

install: venv

api-stop:
	-pkill -f 'python -m uvicorn apps.api.main:app' || true
	-pkill -f 'uvicorn apps.api.main:app' || true
	-fuser -k $(PORT)/tcp || true

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

council-stop:
	-pkill -f 'python -m uvicorn apps.council.main:app' || true
	-pkill -f 'uvicorn apps.council.main:app' || true
	-fuser -k $(COUNCIL_PORT)/tcp || true

council:
	. $(VENV_BIN)/activate && \
	python -m uvicorn apps.council.main:app --host 0.0.0.0 --port $(COUNCIL_PORT)

council-dev:
	. $(VENV_BIN)/activate && \
	python -m uvicorn apps.council.main:app --host 0.0.0.0 --port $(COUNCIL_PORT) --reload

council-restart: council-stop
	@sleep 1
	@$(MAKE) council

council-health:
	curl -sS http://localhost:$(COUNCIL_PORT)/health | python3 -m json.tool

axiomatizer-stop:
	-pkill -f 'python -m uvicorn apps.axiomatizer.main:app' || true
	-pkill -f 'uvicorn apps.axiomatizer.main:app' || true
	-fuser -k $(AXIOMATIZER_PORT)/tcp || true

axiomatizer:
	. $(VENV_BIN)/activate && \
	python -m uvicorn apps.axiomatizer.main:app --host 0.0.0.0 --port $(AXIOMATIZER_PORT)

axiomatizer-dev:
	. $(VENV_BIN)/activate && \
	python -m uvicorn apps.axiomatizer.main:app --host 0.0.0.0 --port $(AXIOMATIZER_PORT) --reload

axiomatizer-restart: axiomatizer-stop
	@sleep 1
	@$(MAKE) axiomatizer

axiomatizer-health:
	curl -sS http://localhost:$(AXIOMATIZER_PORT)/health | python3 -m json.tool

lint:
	. $(VENV_BIN)/activate && \
	python -m ruff check apps packages

test:
	. $(VENV_BIN)/activate && \
	pytest
