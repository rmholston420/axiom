"""WikiPage Neo4j schema — constraints and indexes for the wiki layer."""

from __future__ import annotations

from neo4j import AsyncDriver


async def ensure_wiki_schema(driver: AsyncDriver) -> None:
    """Create WikiPage constraints and indexes if they do not exist.
    Call this alongside ensure_schema() at startup.
    """
    stmts = [
        """
        CREATE CONSTRAINT wiki_page_id_unique IF NOT EXISTS
        FOR (w:WikiPage) REQUIRE w.page_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT wiki_page_slug_unique IF NOT EXISTS
        FOR (w:WikiPage) REQUIRE w.slug IS UNIQUE
        """,
        """
        CREATE INDEX wiki_page_type_index IF NOT EXISTS
        FOR (w:WikiPage) ON (w.page_type)
        """,
        """
        CREATE INDEX wiki_page_generated_index IF NOT EXISTS
        FOR (w:WikiPage) ON (w.generated_at)
        """,
        """
        CREATE INDEX wiki_page_version_index IF NOT EXISTS
        FOR (w:WikiPage) ON (w.version)
        """,
    ]
    async with driver.session() as session:
        for stmt in stmts:
            await session.run(stmt.strip())
