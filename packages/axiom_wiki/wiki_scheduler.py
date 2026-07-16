"""WikiScheduler — detects new/changed graph nodes and triggers incremental
wiki page regeneration.

Runs as a background asyncio task or standalone async loop.
Design:
  - Uses a Redis/Valkey set `axiom:wiki:dirty` to track pending regenerations.
  - The research queue_worker enqueues dirty node IDs after writing to Neo4j.
  - The scheduler drains the dirty set on each tick and calls WikiGenerator.
  - Pages are only regenerated when content_hash would change (detected via
    the ON MATCH version increment in the UPSERT cypher).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable

from neo4j import AsyncDriver

from axiom_wiki.wiki_generator import WikiGenerator
from axiom_wiki.wiki_models import WikiPage

logger = logging.getLogger(__name__)

DIRTY_SET_KEY = "axiom:wiki:dirty"
DEFAULT_TICK_SECONDS = 60
DEFAULT_BATCH_SIZE = 20


class WikiScheduler:
    """Background scheduler that drains a dirty-node queue and regenerates pages."""

    def __init__(
        self,
        generator: WikiGenerator,
        redis_client: Any,  # aioredis / valkey-glide client
        tick_seconds: int = DEFAULT_TICK_SECONDS,
        batch_size: int = DEFAULT_BATCH_SIZE,
        on_page_generated: Callable[[WikiPage], None] | None = None,
    ) -> None:
        self._gen = generator
        self._redis = redis_client
        self._tick = tick_seconds
        self._batch = batch_size
        self._on_page = on_page_generated
        self._running = False

    # ------------------------------------------------------------------
    # Public control
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the scheduler loop (blocks until stop() called)."""
        self._running = True
        logger.info("WikiScheduler started (tick=%ds, batch=%d)", self._tick, self._batch)
        while self._running:
            try:
                await self._tick_once()
            except Exception:
                logger.exception("WikiScheduler tick error")
            await asyncio.sleep(self._tick)

    def stop(self) -> None:
        self._running = False

    @classmethod
    async def enqueue_dirty(
        cls, redis_client: Any, node_type: str, node_id: str
    ) -> None:
        """Enqueue a node for wiki regeneration. Call from queue_worker after writes."""
        member = f"{node_type}:{node_id}"
        await redis_client.sadd(DIRTY_SET_KEY, member)
        logger.debug("Enqueued wiki dirty: %s", member)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _tick_once(self) -> None:
        members = await self._redis.spop(DIRTY_SET_KEY, self._batch)
        if not members:
            return
        logger.info("WikiScheduler processing %d dirty nodes", len(members))
        for raw in members:
            member = raw.decode() if isinstance(raw, bytes) else raw
            await self._process_member(member)

    async def _process_member(self, member: str) -> None:
        """Dispatch regeneration based on node type prefix."""
        try:
            node_type, _, node_id = member.partition(":")
            page: WikiPage | None = None
            if node_type == "query":
                page = await self._gen.generate_query_page(node_id)
            elif node_type == "axiom":
                page = await self._gen.generate_axiom_page(node_id)
            elif node_type == "source":
                page = await self._gen.generate_source_page(node_id)
            else:
                logger.warning("Unknown wiki dirty node type: %s", node_type)
                return
            if page and self._on_page:
                self._on_page(page)
            logger.info("Wiki page regenerated: %s v%d", page.page_id if page else member, page.version if page else 0)
        except Exception:
            logger.exception("Failed to regenerate wiki page for: %s", member)


# mypy/pyright: Any import
try:
    from typing import Any  # noqa: F811
except ImportError:
    pass
