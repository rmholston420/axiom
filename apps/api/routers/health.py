"""Health check router — verifies connectivity to all pre-existing services.

Neo4j check uses a lightweight query on the shared lifespan driver to avoid
leaking a new driver connection per health-check request.
"""

import asyncio

import httpx
from fastapi import APIRouter, Request
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
    """Re-use the lifespan driver; fall back to a fresh driver if unavailable."""
    try:
        driver = getattr(getattr(request.app, "state", None), "driver", None)
        if driver is None:
            from neo4j import AsyncGraphDatabase
            driver = AsyncGraphDatabase.driver(
                settings.axiom_neo4j_uri,
                auth=(settings.axiom_neo4j_user, settings.axiom_neo4j_password),
            )
            await driver.verify_connectivity()
            await driver.close()
        else:
            async with driver.session() as session:
                await session.run("RETURN 1")
        return ServiceStatus(name=ServiceName.NEO4J, ok=True)
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
    """Check connectivity to Ollama, SearXNG, Neo4j, and Valkey (concurrently)."""
    _name_map = {
        "ollama": ServiceName.OLLAMA,
        "searxng": ServiceName.SEARXNG,
        "neo4j": ServiceName.NEO4J,
        "valkey": ServiceName.VALKEY,
    }

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
