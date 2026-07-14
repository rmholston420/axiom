# Axiom Architecture Overview

**Axiom — Local Research Workbench**

## Service Map

```
┌─────────────────────────────────────────────────────────┐
│  Browser  →  Axiom Web (Next.js :7100)                  │
│               │                                         │
│               ▼                                         │
│  Axiom API (FastAPI :7200)                              │
│  ├── /jobs        → queue via Valkey :7379              │
│  ├── /sse/:id     → SSE event stream                    │
│  ├── /council     → HTTP → Axiom Council :7201          │
│  ├── /axioms      → HTTP → Axiom Axiomatizer :7202      │
│  └── /graph       → Neo4j :7687                         │
│                                                         │
│  Axiom Council (FastAPI :7201)                          │
│  └── fan-out → Ollama :7434                             │
│                                                         │
│  Axiom Axiomatizer (FastAPI :7202)                      │
│  └── Neo4j :7687 + Ollama :7434                         │
│                                                         │
│  Pre-existing (outside compose):                        │
│  Ollama :7434 | SearXNG :7300 | Neo4j :7687 | Valkey :7379
└─────────────────────────────────────────────────────────┘
```

## Data Flow

1. User submits a question from Axiom Web
2. Axiom API enqueues a job in Valkey and returns a `job_id`
3. Web opens an SSE stream to `/sse/{job_id}`
4. Queue worker picks up the job:
   - Planner (Ollama) generates search sub-queries
   - Retriever fetches results from SearXNG
   - Extractor distils findings
   - Synthesizer (Ollama) writes the report
5. Findings and source nodes are written to Neo4j
6. Final report is stored in job state; SSE `done` event is emitted
7. Council (optional) runs sequential deliberation before synthesis
8. Axiomatizer (optional, feature-toggled) proposes axiom transforms from the report

## Key Design Constraints

- All external infra (Ollama, SearXNG, Neo4j, Valkey) runs outside Docker Compose
- 16GB VRAM → sequential council mode by default
- `AXIOM_AXIOMATIZER_ENABLED=false` by default
- No external cloud services; fully local
