"""Neo4j schema bootstrap — constraints and indexes."""
from __future__ import annotations

from neo4j import AsyncDriver


async def ensure_schema(driver: AsyncDriver) -> None:
    """Create uniqueness constraints and indexes if they do not exist yet."""
    stmts = [
        # Uniqueness constraints
        """
        CREATE CONSTRAINT query_id_unique IF NOT EXISTS
        FOR (q:Query) REQUIRE q.id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT finding_id_unique IF NOT EXISTS
        FOR (f:Finding) REQUIRE f.id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT source_url_unique IF NOT EXISTS
        FOR (s:Source) REQUIRE s.url IS UNIQUE
        """,
        # Indexes for common look-ups
        """
        CREATE INDEX query_text_index IF NOT EXISTS
        FOR (q:Query) ON (q.text)
        """,
        """
        CREATE INDEX finding_created_index IF NOT EXISTS
        FOR (f:Finding) ON (f.created_at)
        """,
    ]
    async with driver.session() as session:
        for stmt in stmts:
            await session.run(stmt.strip())
