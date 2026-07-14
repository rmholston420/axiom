"""Neo4j repository — CRUD for Query, Finding, Source, and Axiom nodes."""
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
    # Axiom nodes  (Slice 6)
    # ------------------------------------------------------------------

    async def create_axiom(
        self,
        axiom_id: str,
        label: str,
        statement: str,
        justification: str,
        confidence: float,
        approved: bool = True,
        eval_reason: str = "",
    ) -> str:
        """Persist an Axiom node (MERGE on id — idempotent). Returns axiom_id."""
        cypher = """
        MERGE (a:Axiom {id: $id})
        ON CREATE SET
            a.label         = $label,
            a.statement     = $statement,
            a.justification = $justification,
            a.confidence    = $confidence,
            a.approved      = $approved,
            a.eval_reason   = $eval_reason,
            a.created_at    = $created_at
        ON MATCH SET
            a.statement     = $statement,
            a.justification = $justification,
            a.confidence    = $confidence,
            a.approved      = $approved,
            a.eval_reason   = $eval_reason
        RETURN a.id AS id
        """
        async with self._driver.session() as session:
            await session.run(
                cypher,
                id=axiom_id,
                label=label,
                statement=statement,
                justification=justification,
                confidence=float(confidence),
                approved=approved,
                eval_reason=eval_reason,
                created_at=_now(),
            )
        return axiom_id

    async def get_axiom(self, axiom_id: str) -> dict[str, Any] | None:
        """Fetch a single Axiom node by id."""
        cypher = "MATCH (a:Axiom {id: $id}) RETURN a"
        async with self._driver.session() as session:
            result = await session.run(cypher, id=axiom_id)
            record = await result.single()
            if record is None:
                return None
            return dict(record["a"])

    async def list_axioms(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return up to `limit` Axiom nodes ordered newest-first."""
        cypher = """
        MATCH (a:Axiom)
        RETURN a
        ORDER BY a.created_at DESC
        LIMIT $limit
        """
        async with self._driver.session() as session:
            result = await session.run(cypher, limit=limit)
            return [dict(r["a"]) async for r in result]

    # ------------------------------------------------------------------
    # Read helpers (pre-existing)
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
