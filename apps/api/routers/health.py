"""Health check router — verifies connectivity to all pre-existing services."""
import asyncio
from fastapi import APIRouter
import httpx
from neo4j import AsyncGraphDatabase
from redis.asyncio import Redis

from axiom_core.models import HealthResponse, ServiceStatus
from axiom_core.enums import ServiceName
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


async def _check_neo4j() -> ServiceStatus:
    try:
        driver = AsyncGraphDatabase.driver(
            settings.axiom_neo4j_uri,
            auth=(settings.axiom_neo4j_user, settings.axiom_neo4j_password),
        )
        await driver.verify_connectivity()
        await driver.close()
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
async def health_check():
    """Check connectivity to Ollama, SearXNG, Neo4j, and Valkey (concurrently)."""
    _name_map = {
        _check_ollama: ServiceName.OLLAMA,
        _check_searxng: ServiceName.SEARXNG,
        _check_neo4j: ServiceName.NEO4J,
        _check_valkey: ServiceName.VALKEY,
    }

    async def bounded(checker, seconds: float = 3.0) -> ServiceStatus:
        try:
            return await asyncio.wait_for(checker(), timeout=seconds)
        except (asyncio.TimeoutError, TimeoutError):
            return ServiceStatus(name=_name_map[checker], ok=False, detail="timeout")
        except Exception as exc:
            return ServiceStatus(name=_name_map[checker], ok=False, detail=str(exc))

    results = await asyncio.gather(
        bounded(_check_ollama),
        bounded(_check_searxng),
        bounded(_check_neo4j),
        bounded(_check_valkey),
    )
    all_ok = all(s.ok for s in results)
    return HealthResponse(
        status="healthy" if all_ok else "degraded",
        services=list(results),
    )
