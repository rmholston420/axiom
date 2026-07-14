# Axiom v1 Build Spec

Axiom should be built as a single monorepo with deployable apps under `apps/` and reusable code under `packages/`, because that keeps shared logic centralized while preserving clean service boundaries.[cite:259][cite:276] The repository root should be `~/axiom/`, and the product subtitle should be **Local Research Workbench** so the brand name is paired with a clear category signal.[cite:235][cite:236]

## Repository root

```text
~/axiom/
├── README.md
├── .env
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Makefile
├── pyproject.toml
├── package.json
├── pnpm-workspace.yaml
├── turbo.json
├── docs/
│   ├── architecture/
│   ├── api/
│   ├── decisions/
│   └── runbooks/
├── infra/
│   ├── docker/
│   ├── scripts/
│   └── neo4j/
├── apps/
│   ├── api/
│   ├── council/
│   ├── axiomatizer/
│   └── web/
├── packages/
│   ├── axiom_core/
│   ├── axiom_research/
│   ├── axiom_graph/
│   ├── axiom_providers/
│   ├── axiom_contracts/
│   └── axiom_ui/
├── tests/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
└── output/
```

This layout follows the common monorepo practice of keeping deployable applications separate from shared libraries and contracts, which makes incremental changes and cross-stack type sharing easier.[cite:260][cite:276]

## Naming rules

Use **Axiom** consistently across services, package names, and UI labels.[cite:263][cite:244]

- Product: **Axiom**
- Subtitle: **Local Research Workbench**
- Service names: **Axiom API**, **Axiom Council**, **Axiom Axiomatizer**, **Axiom Web**
- Python package names: `axiom_core`, `axiom_research`, `axiom_graph`, `axiom_providers`, `axiom_contracts`
- Docker container names: `axiom-api`, `axiom-council`, `axiom-axiomatizer`, `axiom-web`

## Environment variables

Environment variables should use uppercase names with a shared `AXIOM_` prefix so they remain unambiguous across multiple services and deployment environments.[cite:261][cite:268]

```bash
# Pre-existing infrastructure
AXIOM_OLLAMA_BASE_URL=http://host.docker.internal:11434
AXIOM_SEARXNG_URL=http://host.docker.internal:7300
AXIOM_NEO4J_URI=bolt://host.docker.internal:7687
AXIOM_NEO4J_USER=neo4j
AXIOM_NEO4J_PASSWORD=collosus
AXIOM_REDIS_URL=redis://host.docker.internal:6379

# New Axiom services
AXIOM_API_PORT=7200
AXIOM_COUNCIL_PORT=7201
AXIOM_AXIOMATIZER_PORT=7202
AXIOM_WEB_PORT=7100

# Default models
AXIOM_MODEL_PLANNER=qwen3:14b
AXIOM_MODEL_SYNTHESIZER=qwen3:14b
AXIOM_MODEL_CODE=qwen2.5-coder:14b
AXIOM_MODEL_CRITIC=qwen3.5:9b
AXIOM_MODEL_CHAIRMAN=qwen3:14b
AXIOM_MODEL_AXIOMATIZER=qwen3:14b

# Runtime defaults
AXIOM_BREADTH=4
AXIOM_DEPTH=3
AXIOM_MAX_RESULTS_PER_QUERY=5
AXIOM_COUNCIL_SIZE=3
AXIOM_COUNCIL_ENABLED=true
AXIOM_AXIOMATIZER_ENABLED=false
```

## Apps and packages

Anything independently runnable belongs in `apps/`, while anything reused across services belongs in `packages/`.[cite:259][cite:276] This keeps FastAPI apps thin and pushes business logic into shared modules.

### `apps/`

- `apps/api` — FastAPI gateway, queue endpoints, SSE, health checks, graph/data endpoints.
- `apps/council` — FastAPI council fan-out and synthesis service.
- `apps/axiomatizer` — FastAPI axiom modification and evaluation service.
- `apps/web` — Next.js UI for dashboard, graph, settings, and queued jobs.

### `packages/`

- `packages/axiom_core` — settings, enums, shared Pydantic models, runtime config.
- `packages/axiom_research` — planner, retriever, extractor, synthesizer, queue worker logic.
- `packages/axiom_graph` — Neo4j repository layer, graph queries, schema setup.
- `packages/axiom_providers` — Ollama, SearXNG, and Valkey/Redis adapters.
- `packages/axiom_contracts` — OpenAPI-generated client/types and shared schemas.[cite:260]
- `packages/axiom_ui` — optional shared React components once the web app grows.

## Slice sequence

Axiom should still be built vertically, with each slice delivering one working end-to-end path before moving on.[cite:170][cite:88]

### Slice 1 — Scaffold and connectivity

Create the monorepo, root config files, `apps/api`, `apps/web`, and the four core shared packages.[cite:259] Add a `GET /health` endpoint in Axiom API that verifies connectivity to the pre-existing Ollama, SearXNG, Neo4j, and Valkey instances.[cite:170]

**Smoke test:** `curl http://localhost:7200/health` returns all services healthy.[cite:170]

### Slice 2 — Research loop core

Implement `packages/axiom_research`, `packages/axiom_graph`, and `packages/axiom_providers` so a CLI task can plan via Ollama, search via SearXNG, write findings to Neo4j, and synthesize a report.[cite:170]

**Smoke test:** run a CLI query and confirm `Query`, `Finding`, and `Source` nodes are created in Neo4j.[cite:170]

### Slice 3 — API, queue, and stream

Wire the research loop into `apps/api`, with REST endpoints for job creation, queue listing, per-job status, SSE streaming, settings, models, and graph data.[cite:170] The queue should use your pre-existing Valkey/Redis endpoint rather than spinning up a new queue service.[cite:170]

**Smoke test:** enqueue a job, watch live SSE events, confirm final report stored in job state.[cite:170]

### Slice 4 — Web UI

Build `apps/web` as a Next.js TypeScript app with three core pages: dashboard, graph, and settings.[cite:170] The dashboard should show queued jobs, a live event stream, and final report output, while keeping the UI minimal and browser-first.[cite:170]

**Smoke test:** submit a question from the browser and watch it complete end to end.[cite:170]

### Slice 5 — Council

Add `apps/council` and route council requests through HTTP from Axiom API rather than importing council code directly, preserving service boundaries.[cite:170] On a 16GB card, the default mode should be sequential or lightweight council rather than parallel large-model fan-out, to avoid VRAM pressure.[cite:186][cite:212]

**Smoke test:** `POST /council` returns consensus/disagreement structure.[cite:186]

### Slice 6 — Axiomatizer

Add `apps/axiomatizer` and connect it to the web settings and graph subsystems so axioms can be proposed, evaluated, and stored as graph objects.[cite:89] This service should remain optional behind a feature toggle in early versions.[cite:170]

**Smoke test:** submit an axiom transform request and confirm the new axiom persists in Neo4j.[cite:89]

### Slice 7 — Hardening

Add Dockerfiles only for the new Axiom services, not for Ollama, SearXNG, Neo4j, or Valkey, since those are already running outside the repo.[cite:170] Add linting, tests, docs, and ADRs so the monorepo remains understandable as it grows.[cite:282][cite:283]

**Smoke test:** `docker compose up -d` brings up Axiom API, Axiom Council, Axiom Axiomatizer, and Axiom Web successfully while connecting to the existing local infrastructure.[cite:170]

## Root files

Axiom should start with these top-level files:

- `README.md` — setup, quickstart, ports, architecture summary.
- `.env.example` — all `AXIOM_` variables documented.[cite:261]
- `pyproject.toml` — Python workspace and shared dependencies.
- `package.json` + `pnpm-workspace.yaml` — JS workspace root.
- `turbo.json` — task orchestration for builds and checks.[cite:276]
- `Makefile` — thin wrappers for setup, run, lint, test, and compose targets.
- `docs/decisions/` — ADRs for major architecture decisions, which is a recommended way to keep technical reasoning close to the codebase.[cite:282][cite:283]

## Recommended defaults

For the current hardware target, the best default role assignment remains:

- Planner: `qwen3:14b`
- Synthesizer: `qwen3:14b`
- Code: `qwen2.5-coder:14b`
- Critic: `qwen3.5:9b`
- Chairman: `qwen3:14b`
- Axiomatizer: `qwen3:14b`.[cite:186][cite:210][cite:212]

That keeps the system aligned with the 16GB VRAM constraint while reserving the smaller model for faster supporting roles.[cite:186][cite:212]

## Immediate scaffold

The first repository creation command should now be:

```bash
mkdir -p ~/axiom/{docs/{architecture,api,decisions,runbooks},infra/{docker,scripts,neo4j},apps/{api,council,axiomatizer,web},packages/{axiom_core,axiom_research,axiom_graph,axiom_providers,axiom_contracts,axiom_ui},tests/{integration,e2e,fixtures},output}
```

Then create the root files:

```bash
cd ~/axiom
touch README.md .env .env.example .gitignore docker-compose.yml Makefile pyproject.toml package.json pnpm-workspace.yaml turbo.json
```

This updated spec makes **Axiom** internally consistent as a product, repository, and service architecture, while staying faithful to the local-first, queue-based, graph-backed research design.[cite:170][cite:89]
