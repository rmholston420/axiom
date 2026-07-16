# ADR-004: Graph-First Wiki Generation

**Status:** Accepted  
**Date:** 2026-07-16  
**Author:** rmholston

## Context

Axiom accumulates Query, Finding, Source, and Axiom nodes in Neo4j as research
jobs run. As the graph grows, there is no human-readable view that surfaces
connections across topics and axioms. Hand-authoring a wiki is not scalable.

## Decision

We add a **graph-first wiki layer** implemented as `packages/axiom_wiki` that:

1. **Reads graph neighbourhoods** from Neo4j — a Query and its Findings and
   Sources form a Topic page; an Axiom node and its connected evidence form an
   Axiom page; a Source node and its citing Findings form a Source page.
2. **Synthesises wiki pages** via a local Ollama call using the same model
   infrastructure already established in `axiom_research`.
3. **Stores rendered pages as WikiPage nodes** in Neo4j with `GENERATED_FROM`
   edges back to their anchor nodes. This keeps the wiki queryable via Cypher.
4. **Regenerates incrementally** — a `WikiScheduler` drains a Redis/Valkey
   dirty-node set (`axiom:wiki:dirty`) populated by the research queue worker
   after each write. Only affected page neighbourhoods are re-synthesised.
5. **Versions pages** — every upsert increments `w.version` and stores a
   `content_hash` so diffs can be computed without full-text comparison.

## Page types

| Type | Anchor node | Sections |
|------|-------------|----------|
| `topic` | `Query` | Overview, Key Findings, Open Questions |
| `axiom` | `Axiom` | Statement, Justification, Supporting Evidence, Contradictions |
| `source` | `Source` | About This Source, Key Contributions, Limitations |
| `entity` | reserved | (future: NER-extracted entities) |

## Alternatives considered

- **RAG-first wiki**: chunk documents, embed them, retrieve per topic. Ruled out
  because Axiom's primary store is already a graph; reading from Neo4j directly
  avoids a second embedding layer and keeps citations structurally precise.
- **Static markdown files**: no automatic growth, brittle, not queryable.
- **Dedicated wiki database (MediaWiki)**: operational overhead, no graph query
  capability, disconnected from research data model.

## Consequences

- WikiPage nodes add ~5 properties and 1-2 edges per page to Neo4j. At 10k
  pages this is negligible.
- Ollama latency per page generation is 5-30 s depending on model. The scheduler
  runs asynchronously so it does not block research jobs.
- The wiki router (`GET /wiki/pages`, `GET /wiki/pages/{id}`,
  `POST /wiki/generate/*`) gives the Next.js web app a stable API surface.
- A future `entity` page type will require NER extraction (e.g. spaCy or an
  Ollama-backed structured prompt), tracked in a follow-up ADR.
