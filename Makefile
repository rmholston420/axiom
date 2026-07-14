.PHONY: setup install lint lint-py lint-js format test test-integration test-e2e \
        compose-up compose-down compose-logs compose-build health

# ── Setup ──────────────────────────────────────────────────────────────────────
setup: install

install:
	pip install -e ".[dev]"
	corepack enable
	pnpm install

# ── Lint ───────────────────────────────────────────────────────────────────────
lint: lint-py lint-js

lint-py:
	ruff check .
	ruff format --check .

lint-js:
	pnpm --filter axiom-web exec next lint

# ── Format ─────────────────────────────────────────────────────────────────────
format:
	ruff format .
	ruff check --fix .

# ── Tests ──────────────────────────────────────────────────────────────────────
test:
	pytest -m "not integration and not e2e"

test-integration:
	pytest -m integration

test-e2e:
	pytest -m e2e

# ── Docker ─────────────────────────────────────────────────────────────────────
compose-up:
	docker compose up -d

compose-down:
	docker compose down --remove-orphans

compose-logs:
	docker compose logs -f

compose-build:
	docker compose build --no-cache

# ── Health ─────────────────────────────────────────────────────────────────────
health:
	@echo "--- Axiom API ---"
	@curl -sf http://localhost:7200/health | python3 -m json.tool || echo "UNREACHABLE"
	@echo "--- Axiom Council ---"
	@curl -sf http://localhost:7201/health | python3 -m json.tool || echo "UNREACHABLE"
	@echo "--- Axiom Axiomatizer ---"
	@curl -sf http://localhost:7202/health | python3 -m json.tool || echo "UNREACHABLE"
	@echo "--- Axiom Web ---"
	@curl -sf http://localhost:7100/ > /dev/null && echo "OK" || echo "UNREACHABLE"
