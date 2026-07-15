# Testing Guide

This repository uses a layered testing strategy so changes can be validated quickly during development and more thoroughly before merging.

## Test layers

The automated test suite currently has two main layers:

- **Unit tests** in `tests/unit/` validate small behaviors in isolation, including router branches, dependency helpers, worker logic, parsing, and research pipeline components.
- **API smoke tests** in `tests/integration/test_api_smoke.py` validate a small set of high-value routes through the FastAPI app using a `TestClient` and controlled dependency overrides instead of real backing services.

This split keeps feedback fast. Unit tests catch detailed regressions, while smoke tests verify that the app still boots correctly and serves the most important API surfaces end to end.

## Running tests

Use the following commands from the repository root inside the project virtual environment.

### Smoke suite

```bash
pytest tests/integration/test_api_smoke.py -v
```

Use this when making API, dependency wiring, routing, or serialization changes and a quick confidence check is needed.

### Unit suite

```bash
pytest tests/unit -v
```

Use this when changing application logic, router internals, providers, parsers, workers, or shared models.

### Full fast local check

```bash
pytest tests/integration/test_api_smoke.py -v
pytest tests/unit -v
```

This two-step sequence is the best default local verification path because it confirms both top-level API wiring and detailed behavior without introducing external service dependencies.

## Current baseline

The latest verified local run established this baseline:

- `pytest tests/integration/test_api_smoke.py -v` collected 3 tests and all 3 passed.
- `pytest tests/unit -v` collected 105 tests and all 105 passed.

If a future change breaks that baseline, investigate the dependency contract for the affected route before expanding test doubles unnecessarily.

## Smoke test design

The smoke suite is intentionally small and deterministic. It is designed to exercise important routes without requiring live Neo4j, Valkey, council, axiomatizer, or a real research loop.

`tests/integration/test_api_smoke.py` uses `app.dependency_overrides[...]` to replace runtime dependencies with in-memory dummies before constructing a `TestClient`. This approach makes the tests fast, reproducible, and suitable for local development and CI.

### Current coverage

The smoke suite currently verifies the following route groups:

- `/`, `/health`, and `/settings` for basic service availability and configuration payload shape.
- `/jobs`, `/jobs/{id}`, and `/jobs/{id}/stream` for job creation, listing, retrieval, and SSE stream response behavior.
- `/models` for the expected response envelope containing a `models` list.
- `/graph` for graph payload shape and filtered graph edges using a dummy graph driver.

## Dummy backends

The smoke tests rely on lightweight in-memory stand-ins that implement only the parts of each dependency that the API actually uses.

### Valkey and job storage

`DummyValkeyClient`, `DummyPubSub`, and `DummyValkey` simulate the subset of Valkey behavior needed by job storage and streaming:

- Hash reads and writes for job records.
- List push behavior for queue insertion.
- Pub/sub creation, channel subscription, message iteration, and cleanup hooks.

This lets the smoke tests cover job lifecycle and stream endpoints without any real networked datastore.

### Queue worker

`DummyWorker` subclasses `QueueWorker` but overrides behavior so it never touches the real research loop.

- `enqueue()` stores a queued job in the in-memory `JobStore`.
- `run_forever()` is a no-op for test purposes.

This preserves the API contract without starting background processing.

### Graph driver

The graph smoke test uses `DummyResult`, `DummySession`, and `DummyDriver`, following the same contract used by the graph router unit tests.

- `DummySession` supports `async with` and `run()`.
- `DummyResult` supports async iteration over rows.
- `DummyDriver.session()` returns node rows on the first call and edge rows on later calls.

That behavior matches how the `/graph` endpoint loads nodes first and then loads edges. The smoke test verifies that the response contains the expected node IDs and only the filtered links whose endpoints are present in the node set.

## How overrides are wired

The helper that constructs the `TestClient` creates all dummy dependencies first and then attaches them to the FastAPI app through `app.dependency_overrides`.

At minimum, the smoke helper currently overrides:

- `get_valkey`
- `get_job_store`
- `get_worker`
- `get_driver`

This pattern should be preferred over mutating broad application state where possible because it keeps each test dependency explicit and tied to the route contract being exercised.

## Adding new smoke tests

When adding another smoke test, keep it minimal and centered on route contract rather than implementation detail.

1. Identify the route’s direct dependencies.
2. Create the smallest possible dummy object that satisfies the methods and data shape the route needs.
3. Override those dependencies in the shared smoke helper with `app.dependency_overrides`.
4. Assert only the most important response behavior: status code, payload shape, and one or two representative values.
5. Keep external services out of the test unless the purpose of the test is explicitly to validate real integration behavior.

A good example is the `/graph` smoke test. It does not try to validate Neo4j connectivity or Cypher correctness directly. Instead, it verifies that the route returns status 200, emits the expected node IDs, and filters links down to edges whose endpoints exist in the node payload.

## Suggested conventions

To keep the smoke suite maintainable:

- Prefer one shared helper for constructing the overridden `TestClient` unless a route genuinely needs a different setup.
- Keep dummy implementations intentionally small; only add methods when a route requires them.
- Reuse patterns already proven in unit tests when possible.
- Avoid assertions on internal call order unless that behavior is part of the route contract.
- Do not depend on real service availability for smoke tests.

## CI recommendation

The smoke suite is a strong candidate for an early CI gate because it is fast and validates top-level API behavior without infrastructure dependencies.

A practical pipeline order is:

1. Run smoke tests first for fast failure on broken app wiring.
2. Run unit tests second for deeper behavioral coverage.
3. Reserve heavier end-to-end or environment-dependent checks for later pipeline stages.

## Maintenance notes

If a smoke test starts failing after a route refactor, check the dependency contract before expanding the dummy implementation blindly.

A recent example was the `/graph` smoke test. The initial failure happened because the smoke helper did not provide a driver override, which caused an `AttributeError` for missing `app.state.driver`. The durable fix was to override `get_driver` directly with a `DummyDriver` matching the unit-test contract.

That pattern is the preferred model for future smoke coverage additions:

- Isolate the route.
- Mirror the smallest dependency contract that route requires.
- Assert the public response shape.
