# Axiom v0.2.1

Axiom v0.2.1 is a patch release that finalizes test-alignment work, restores a fully green unit suite, and records the project as complete across all planned delivery slices.

## Highlights

- Green unit suite on `main` with 103 passing tests and ~97% total coverage.
- Planner fallback assertions now match real `SubQuery` behavior, including bullet-preserving parse output.
- API lifespan assertions now match current startup/shutdown behavior.
- All planned slices are now complete across the Axiom monorepo.

## Included in this release

### Fixed
- Corrected the API lifespan test to assert startup and shutdown log behavior instead of expecting the yielded app object.
- Updated the planner fallback branch test to match actual `SubQuery` output, including bullet-preserving fallback parsing.
- Restored the full unit suite to green on `main` after aligning branch tests with current runtime behavior.

### Project status
- All planned slices are now complete:
  - [x] Slice 1 — Scaffold and connectivity
  - [x] Slice 2 — Research loop core
  - [x] Slice 3 — API, queue, and stream
  - [x] Slice 4 — Web UI
  - [x] Slice 5 — Council
  - [x] Slice 6 — Axiomatizer
  - [x] Slice 7 — Hardening

### Internal
- Verified unit coverage remains at 97.03% with branch coverage comfortably above the required threshold.
- Added `CHANGELOG.md` and surfaced release visibility in `README.md`.
- Tagged the stable snapshot as `v0.2.1`.

See also: [CHANGELOG.md](./CHANGELOG.md)
