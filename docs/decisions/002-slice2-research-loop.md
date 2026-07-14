# ADR 002 — Slice 2: Research Loop Core

**Status:** Accepted  
**Date:** 2026-07-14

## Context

Slice 2 must wire Ollama, SearXNG, and Neo4j into a single end-to-end research
loop reachable from a CLI command, producing `Query`, `Finding`, and `Source`
nodes in the graph.

## Decision

- `axiom_providers` owns all I/O adapters (Ollama, SearXNG, Valkey). Each
  adapter is a plain async class with a minimal interface.
- `axiom_graph` owns the Neo4j driver session, schema bootstrap (`ensure_schema`
  is idempotent), and the `GraphRepository` CRUD layer.
- `axiom_research` owns the four pipeline stages (Planner → Retriever → Extractor
  → Synthesizer) and the `ResearchLoop` orchestrator that wires them together.
- `scripts/research.py` is the CLI smoke-test entry point for Slice 2. It adds
  each `packages/*` directory to `sys.path` at import time so no install step is
  required during development.
- JSON parsing in the Planner is defensive: it strips markdown fences and falls
  back to line-by-line splitting if Ollama returns malformed JSON.

## Consequences

- The research loop is independently testable without the FastAPI layer.
- Slice 3 will import `ResearchLoop` directly and wrap it in a queue worker.
- No additional Python dependencies are introduced beyond what `pyproject.toml`
  already declares.
