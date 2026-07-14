# Runbook — Docker Operations

## Start all Axiom services

```bash
# From repo root
docker compose up -d
```

This starts `axiom-api`, `axiom-council`, `axiom-axiomatizer`, and `axiom-web`.
Ollama, SearXNG, Neo4j, and Valkey must already be running on the host.

## Check service health

```bash
docker compose ps
curl -s http://localhost:7200/health | python3 -m json.tool
curl -s http://localhost:7201/health | python3 -m json.tool
curl -s http://localhost:7202/health | python3 -m json.tool
```

## View logs

```bash
# All services
docker compose logs -f

# Single service
docker compose logs -f axiom-api
```

## Rebuild after code changes

```bash
docker compose build --no-cache axiom-api
docker compose up -d axiom-api
```

## Stop all services

```bash
docker compose down
```

## Full teardown (removes containers, not volumes)

```bash
docker compose down --remove-orphans
```
