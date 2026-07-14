# Runbook — Local Development (without Docker)

## Prerequisites

- Python 3.11+
- Node 20+
- pnpm (`corepack enable`)
- Ollama running on port 7434
- SearXNG running on port 7300
- Neo4j running on port 7687
- Valkey running on port 7379

## Setup

```bash
# Clone and enter repo
git clone https://github.com/rmholston420/axiom.git ~/axiom
cd ~/axiom

# Copy env file and fill in any overrides
cp .env.example .env

# Install Python dependencies
pip install -e ".[dev]"

# Install JS dependencies
corepack enable
pnpm install
```

## Run services locally

```bash
# Terminal 1 — Axiom API
uvicorn apps.api.main:app --host 0.0.0.0 --port 7200 --reload

# Terminal 2 — Axiom Council
uvicorn apps.council.main:app --host 0.0.0.0 --port 7201 --reload

# Terminal 3 — Axiom Axiomatizer
uvicorn apps.axiomatizer.main:app --host 0.0.0.0 --port 7202 --reload

# Terminal 4 — Axiom Web
cd apps/web && pnpm dev
```

## Run linters

```bash
make lint
```

## Run unit tests

```bash
make test
```

## Run integration tests (requires live stack)

```bash
make test-integration
```
