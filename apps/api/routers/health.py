"""Health check router — verifies connectivity to all pre-existing services."""

import asyncio

import httpx
from fastapi import APIRouter, Request
from neo4j import AsyncGraphDatabase
from redis.asyncio import Redis

from axiom_core.enums import ServiceName
from axiom_core.models import HealthResponse, ServiceStatus
from axiom_core.settings import settings

router = APIRouter(tags=["health"])


async def _check_ollama() -> ServiceStatus:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{settings.axiom_ollama_base_url}/api/tags")
        return ServiceStatus(name=ServiceName.OLLAMA, ok=r.status_code == 200)
    except Exception as exc:
        return ServiceStatus(name=ServiceName.OLLAMA, ok=False, detail=str(exc))


async def _check_searxng() -> ServiceStatus:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{settings.axiom_searxng_url}/healthz")
        return ServiceStatus(name=ServiceName.SEARXNG, ok=r.status_code == 200)
    except Exception as exc:
        return ServiceStatus(name=ServiceName.SEARXNG, ok=False, detail=str(exc))


async def _check_neo4j(request: Request) -> ServiceStatus:
    """
    Prefer the lifespan driver when available.
    Keep AsyncGraphDatabase imported at module scope so tests can monkeypatch it.
    """
    try:
        driver = getattr(getattr(request.app, "state", None), "driver", None)

        if driver is not None:
            # Existing tests expect a lightweight session probe.
            async with driver.session() as session:
                await session.run("RETURN 1")
            return ServiceStatus(name=ServiceName.NEO4J, ok=True)

        fresh = AsyncGraphDatabase.driver(
            settings.axiom_neo4j_uri,
            auth=(settings.axiom_neo4j_user, settings.axiom_neo4j_password),
        )
        try:
            await fresh.verify_connectivity()
            return ServiceStatus(name=ServiceName.NEO4J, ok=True)
        finally:
            await fresh.close()

    except Exception as exc:
        return ServiceStatus(name=ServiceName.NEO4J, ok=False, detail=str(exc))


async def _check_valkey() -> ServiceStatus:
    try:
        r = Redis.from_url(settings.axiom_redis_url, socket_connect_timeout=3)
        await r.ping()
        await r.aclose()
        return ServiceStatus(name=ServiceName.VALKEY, ok=True)
    except Exception as exc:
        return ServiceStatus(name=ServiceName.VALKEY, ok=False, detail=str(exc))


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    """Check connectivity to Ollama, SearXNG, Neo4j, and Valkey concurrently."""
    async def bounded_ollama(seconds: float = 3.0) -> ServiceStatus:
        try:
            return await asyncio.wait_for(_check_ollama(), timeout=seconds)
        except TimeoutError:
            return ServiceStatus(name=ServiceName.OLLAMA, ok=False, detail="timeout")
        except Exception as exc:
            return ServiceStatus(name=ServiceName.OLLAMA, ok=False, detail=str(exc))

    async def bounded_searxng(seconds: float = 3.0) -> ServiceStatus:
        try:
            return await asyncio.wait_for(_check_searxng(), timeout=seconds)
        except TimeoutError:
            return ServiceStatus(name=ServiceName.SEARXNG, ok=False, detail="timeout")
        except Exception as exc:
            return ServiceStatus(name=ServiceName.SEARXNG, ok=False, detail=str(exc))

    async def bounded_neo4j(seconds: float = 3.0) -> ServiceStatus:
        try:
            return await asyncio.wait_for(_check_neo4j(request), timeout=seconds)
        except TimeoutError:
            return ServiceStatus(name=ServiceName.NEO4J, ok=False, detail="timeout")
        except Exception as exc:
            return ServiceStatus(name=ServiceName.NEO4J, ok=False, detail=str(exc))

    async def bounded_valkey(seconds: float = 3.0) -> ServiceStatus:
        try:
            return await asyncio.wait_for(_check_valkey(), timeout=seconds)
        except TimeoutError:
            return ServiceStatus(name=ServiceName.VALKEY, ok=False, detail="timeout")
        except Exception as exc:
            return ServiceStatus(name=ServiceName.VALKEY, ok=False, detail=str(exc))

    results = await asyncio.gather(
        bounded_ollama(),
        bounded_searxng(),
        bounded_neo4j(),
        bounded_valkey(),
    )
    all_ok = all(s.ok for s in results)
    return HealthResponse(
        status="healthy" if all_ok else "degraded",
        services=list(results),
        version="0.6.0",
    )
