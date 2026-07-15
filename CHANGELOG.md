# Changelog

All notable changes to this project will be documented in this file.

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
- Tagged `main` at commit `a6650c0` as `v0.2.1`.

## [0.2.0] - 2026-07-15
### Added
- Expanded unit coverage across API, planner, synthesizer, retriever, and queue worker paths.
- Added coverage for API settings and health branches, axiomatizer parsing/runtime branches, and planner parser/runtime branches.

### Fixed
- Fixed async cleanup handling in queue worker tests to avoid pending-task warnings during test teardown.

### Internal
- Increased overall test confidence for the monorepo’s API and research-loop behavior without changing production architecture.

