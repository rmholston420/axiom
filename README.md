# Axiom

## Releases

Axiom uses [Semantic Versioning](https://semver.org/) and maintains release notes in [`CHANGELOG.md`](./CHANGELOG.md) following the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

- Current stable snapshot: **v0.2.1** — green unit suite with ~97% coverage across apps and packages.
- Previous release: **v0.2.0** — expanded unit coverage for API, planner, synthesizer, retriever, and queue worker paths.


**Local Research Workbench**

Axiom is a local-first, queue-based, graph-backed research system built as a monorepo.

## Architecture

```
apps/api          FastAPI gateway — health, queue, SSE, graph endpoints  (port 7200)
apps/council      FastAPI council fan-out and synthesis service           (port 7201)
apps/axiomatizer  FastAPI axiom modification and evaluation service       (port 7202)
apps/web          Next.js dashboard, graph viewer, settings               (port 7100)

packages/axiom_core        settings, enums, Pydantic models, runtime config
packages/axiom_research    planner, retriever, extractor, synthesizer, queue worker
packages/axiom_graph       Neo4j repository layer, graph queries, schema
packages/axiom_providers   Ollama, SearXNG, Valkey/Redis adapters
packages/axiom_contracts   shared schemas and OpenAPI types
packages/axiom_ui          shared React components
```

## Prerequisites

These services must already be running locally:

| Service  | Default URL                          |
|----------|--------------------------------------|
| Ollama   | http://localhost:7434                |
| SearXNG  | http://localhost:7300                |
| Neo4j    | bolt://localhost:7687                |
| Valkey   | redis://localhost:7379               |

## Quickstart

```bash
cp .env.example .env          # fill in any values that differ
make install                  # create venv and install all Python packages
make dev                      # start Axiom API in dev mode
curl http://localhost:7200/health  # smoke test
```

## Make targets

| Target         | Description                              |
|----------------|------------------------------------------|
| `make install` | Install all Python deps into .venv       |
| `make dev`     | Run Axiom API with uvicorn --reload      |
| `make lint`    | Run ruff on all packages                 |
| `make test`    | Run pytest                               |
| `make compose` | docker compose up -d (Slice 7+)          |

## Slice status

- [x] Slice 1 — Scaffold and connectivity
- [ ] Slice 2 — Research loop core
- [ ] Slice 3 — API, queue, and stream
- [ ] Slice 4 — Web UI
- [ ] Slice 5 — Council
- [ ] Slice 6 — Axiomatizer
- [ ] Slice 7 — Hardening
