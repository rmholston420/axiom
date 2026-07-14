# ADR-001 — Monorepo Layout

**Date:** 2026-07-14  
**Status:** Accepted  
**Deciders:** rmholston

## Context

Axiom comprises four independently deployable services (API, Council, Axiomatizer, Web) plus
five shared Python packages. We need a repository strategy that keeps shared logic centralized
while preserving clean service boundaries and incremental deployability.

## Decision

Use a single monorepo rooted at `~/axiom/` with:

- `apps/` — independently runnable services (FastAPI + Next.js)
- `packages/` — shared Python libraries consumed by apps
- `tests/` — integration, e2e, and fixture data
- `docs/decisions/` — Architecture Decision Records
- `infra/` — Docker and deployment scripts

## Consequences

**Positive:**
- Single `git clone` to get all code
- Cross-service type sharing via `packages/axiom_contracts`
- One CI pipeline covers all services
- ADRs live next to the code they describe

**Negative:**
- All services share the same `main` branch; discipline required to avoid cross-cutting breakage
- `pnpm-lock.yaml` and Python dep installs cover the full surface

## Alternatives Considered

- **Polyrepo:** Clean boundaries but fragmented CI, harder cross-service type sharing
- **Separate org repos per service:** Too much overhead for a solo/small-team project
