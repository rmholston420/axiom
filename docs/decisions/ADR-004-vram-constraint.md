# ADR-004 — 16GB VRAM Constraint and Model Defaults

**Date:** 2026-07-14  
**Status:** Accepted  
**Deciders:** rmholston

## Context

The target hardware has 16GB VRAM (single GPU). Running multiple large models simultaneously
causes OOM errors or severe slowdowns. Model defaults must respect this constraint.

## Decision

Default to sequential (not parallel) council mode. Use the following model assignments:

| Role | Model | VRAM est. |
|---|---|---|
| Planner | `qwen3:14b` | ~9GB |
| Synthesizer | `qwen3:14b` | ~9GB |
| Code | `qwen2.5-coder:14b` | ~9GB |
| Critic | `qwen3.5:9b` | ~6GB |
| Chairman | `qwen3:14b` | ~9GB |
| Axiomatizer | `qwen3:14b` | ~9GB |

Only one model is loaded at a time in the default configuration. Ollama unloads models
between requests when using sequential mode.

## Consequences

**Positive:**
- No OOM crashes on 16GB card
- Predictable throughput: one model inference at a time

**Negative:**
- Council deliberation is slower (sequential fan-out vs. parallel)
- Users with >24GB VRAM cannot easily enable parallel mode without config changes

## Alternatives Considered

- **Parallel fan-out with smaller models (7B):** Faster but lower quality
- **Single model for all roles:** Simplest, but loses role specialization benefits
