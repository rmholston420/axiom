"""Neo4j repository — CRUD for Query, Finding, and Source nodes."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from neo4j import AsyncDriver


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class GraphRepository:
    """High-level async repository over Neo4j."""

    def __init__(self, driver: AsyncDriver) -> None:
        self._driver = driver

    # ------------------------------------------------------------------
    # Query nodes
    # ------------------------------------------------------------------

    async def create_query(self, text: str, job_id: str | None = None) -> str:
        """Persist a Query node and return its UUID."""
        qid = str(uuid.uuid4())
        cypher = """
        CREATE (q:Query {
            id: $id,
            text: $text,
            job_id: $job_id,
            created_at: $created_at
        })
        RETURN q.id AS id
        """
        async with self._driver.session() as session:
            await session.run(
                cypher,
                id=qid,
                text=text,
                job_id=job_id or "",
                created_at=_now(),
            )
        return qid

    # ------------------------------------------------------------------
    # Source nodes
    # ------------------------------------------------------------------

    async def upsert_source(self, url: str, title: str = "") -> str:
        """Merge a Source node by URL (idempotent) and return its URL."""
        cypher = """
        MERGE (s:Source {url: $url})
        ON CREATE SET s.title = $title, s.created_at = $created_at
        RETURN s.url AS url
        """
        async with self._driver.session() as session:
            await session.run(cypher, url=url, title=title, created_at=_now())
        return url

    # ------------------------------------------------------------------
    # Finding nodes
    # ------------------------------------------------------------------

    async def create_finding(
        self,
        query_id: str,
        sub_query: str,
        summary: str,
        source_urls: list[str],
    ) -> str:
        """Create a Finding node and wire it to its Query and Sources."""
        fid = str(uuid.uuid4())

        create_finding = """
        MATCH (q:Query {id: $query_id})
        CREATE (f:Finding {
            id: $id,
            sub_query: $sub_query,
            summary: $summary,
            created_at: $created_at
        })
        CREATE (q)-[:HAS_FINDING]->(f)
        RETURN f.id AS id
        """
        async with self._driver.session() as session:
            await session.run(
                create_finding,
                query_id=query_id,
                id=fid,
                sub_query=sub_query,
                summary=summary,
                created_at=_now(),
            )
            # Link to each source
            for url in source_urls:
                await session.run(
                    """
                    MATCH (f:Finding {id: $fid})
                    MATCH (s:Source {url: $url})
                    MERGE (f)-[:CITES]->(s)
                    """,
                    fid=fid,
                    url=url,
                )
        return fid

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    async def get_query(self, query_id: str) -> dict[str, Any] | None:
        cypher = "MATCH (q:Query {id: $id}) RETURN q"
        async with self._driver.session() as session:
            result = await session.run(cypher, id=query_id)
            record = await result.single()
            if record is None:
                return None
            return dict(record["q"])

    async def list_findings_for_query(self, query_id: str) -> list[dict[str, Any]]:
        cypher = """
        MATCH (q:Query {id: $id})-[:HAS_FINDING]->(f:Finding)
        RETURN f
        ORDER BY f.created_at
        """
        async with self._driver.session() as session:
            result = await session.run(cypher, id=query_id)
            return [dict(r["f"]) async for r in result]
