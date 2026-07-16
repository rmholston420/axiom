# Changelog

All notable changes to this project will be documented in this file.

## [v0.2.3] - 2026-07-15

### Fixed

- Restored correct axioms web proxy routing to the upstream axiomatizer endpoint so the graph view can load axioms again.
- Fixed long-running council requests through the web proxy by increasing upstream request timeouts, preventing premature 504 failures.
- Repaired SSE streaming for job reports by ensuring `/api/jobs/{id}/stream` proxies to the `axiom-api` container instead of localhost.

### Changed

- Removed the global Next.js `/api/:path*` rewrite in `apps/web/next.config.ts` to avoid misrouting API traffic inside Docker.
- Standardized web-to-API routing around app routes under `apps/web/app/api/...` as the canonical proxy layer.
- Standardized `API_ORIGIN` for containerized environments to use the Docker service name `http://axiom-api:7200` instead of `127.0.0.1`.

### Added

- Added `docs/web-architecture.md` documenting web/API architecture, container-safe origins, timeout expectations, and endpoint validation steps.
- Added a `README.md` section summarizing the known-good web API routing configuration and troubleshooting guidance.


The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]
- No unreleased changes yet.

## [0.2.1] - 2026-07-15
### Fixed
- Corrected the API lifespan test to assert startup and shutdown log behavior instead of expecting the yielded app object.
- Updated the planner fallback branch test to match actual `SubQuery` output, including bullet-preserving fallback parsing.
- Restored the full unit suite to green on `main` after aligning branch tests with current runtime behavior.

### Internal
- Verified unit coverage remains at 97.03% with branch coverage comfortably above the required threshold.
- Confirmed all planned delivery slices are now complete across the monorepo.
- Tagged `main` at commit `a6650c0` as `v0.2.1`.

## [0.2.0] - 2026-07-15
### Added
- Expanded unit coverage across API, planner, synthesizer, retriever, and queue worker paths.
- Added coverage for API settings and health branches, axiomatizer parsing/runtime branches, and planner parser/runtime branches.

### Fixed
- Fixed async cleanup handling in queue worker tests to avoid pending-task warnings during test teardown.

### Internal
- Increased overall test confidence for the monorepo’s API and research-loop behavior without changing production architecture.

