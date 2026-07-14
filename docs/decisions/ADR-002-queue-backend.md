# ADR-002 — Queue Backend: Valkey/Redis

**Date:** 2026-07-14  
**Status:** Accepted  
**Deciders:** rmholston

## Context

Axiom needs a job queue for research tasks that decouples HTTP request acceptance from
long-running Ollama inference. We have a pre-existing Valkey instance on port 7379.

## Decision

Use the pre-existing Valkey (Redis-compatible) instance at `AXIOM_REDIS_URL` for the job
queue. No new queue service is introduced.

## Consequences

**Positive:**
- Zero new infrastructure — Valkey already runs outside the compose file
- Redis-compatible Python client (`redis-py`) works unchanged against Valkey
- Reduces VRAM pressure by not running extra model-serving containers

**Negative:**
- Valkey is not included in `docker-compose.yml`; the host must ensure it is running
- No message replay or persistent consumer groups (acceptable for MVP)

## Alternatives Considered

- **Celery + RabbitMQ:** More features, more infra overhead
- **In-process asyncio queue:** No persistence across restarts
