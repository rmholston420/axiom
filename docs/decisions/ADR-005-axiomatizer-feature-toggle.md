# ADR-005 — Axiomatizer Feature Toggle

**Date:** 2026-07-14  
**Status:** Accepted  
**Deciders:** rmholston

## Context

The Axiomatizer (axiom proposal, evaluation, and storage) is an experimental capability.
Shipping it as always-on in early builds risks exposing unstable behavior to primary workflows.

## Decision

Gate all Axiomatizer functionality behind `AXIOM_AXIOMATIZER_ENABLED` (default: `false`).
When disabled, Axiom API returns 503 for axiom endpoints and the web UI hides the
Axiomatizer settings panel.

## Consequences

**Positive:**
- Primary research workflow is unaffected by Axiomatizer instability
- Feature can be enabled per-deployment without code changes

**Negative:**
- Slightly more conditional logic in Axiom API router

## Alternatives Considered

- **Always-on from Slice 6:** Risk of Axiomatizer bugs surfacing in core research flow
- **Separate branch until stable:** Increases merge complexity
