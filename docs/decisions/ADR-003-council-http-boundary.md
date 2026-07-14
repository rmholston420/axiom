# ADR-003 — Council Service HTTP Boundary

**Date:** 2026-07-14  
**Status:** Accepted  
**Deciders:** rmholston

## Context

The Council (multi-LLM deliberation) can be implemented as a direct Python import inside
Axiom API or as a separate HTTP service. We need to choose the integration pattern.

## Decision

Route all council requests through HTTP from Axiom API to a dedicated `axiom-council`
service on port 7201. Axiom API never imports council Python modules directly.

## Consequences

**Positive:**
- Services can be scaled, restarted, or disabled independently
- `AXIOM_COUNCIL_ENABLED=false` disables the feature by simply not sending HTTP requests
- Council can be replaced with a different implementation without touching Axiom API

**Negative:**
- Extra HTTP hop adds ~1-5ms latency per council call (negligible vs. Ollama inference time)
- Requires `axiom-council` to be healthy for council features to work

## Alternatives Considered

- **Direct Python import:** Tighter coupling, harder to toggle, prevents independent scaling
