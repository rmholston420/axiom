#!/usr/bin/env python
"""CLI entry point for Slice 2 smoke test.

Usage:
    python scripts/research.py "Your research question here"

Requires: Ollama, SearXNG, and Neo4j running locally.
Environment variables are read from .env at the repo root.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv


async def main(question: str) -> None:
    repo_root = Path(__file__).resolve().parent.parent
    packages_root = repo_root / "packages"
    if str(packages_root) not in sys.path:
        sys.path.insert(0, str(packages_root))

    load_dotenv(repo_root / ".env")

    from neo4j import AsyncGraphDatabase
    from axiom_core.settings import settings
    from axiom_research.loop import ResearchLoop

    print("\n🔬 Axiom — Local Research Workbench")
    print(f"   Question : {question}")
    print(f"   Neo4j    : {settings.axiom_neo4j_uri}")
    print(f"   Ollama   : {settings.axiom_ollama_base_url}")
    print(f"   SearXNG  : {settings.axiom_searxng_url}\n")

    driver = AsyncGraphDatabase.driver(
        settings.axiom_neo4j_uri,
        auth=(settings.axiom_neo4j_user, settings.axiom_neo4j_password),
    )

    try:
        loop = ResearchLoop(driver)
        result = await loop.run(question)
    finally:
        await driver.close()

    print("\n" + "=" * 60)
    print("RESEARCH REPORT")
    print("=" * 60)
    print(result.report)
    print("\n" + "=" * 60)
    print(f"Query ID  : {result.query_id}")
    print(f"Findings  : {len(result.findings)}")
    for i, f in enumerate(result.findings, 1):
        print(f"  [{i}] {f.sub_query}  ({len(f.source_urls)} sources)")
    print("\n✅ Smoke test complete — check Neo4j for Query/Finding/Source nodes.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python scripts/research.py "Your question here"')
        sys.exit(1)
    asyncio.run(main(" ".join(sys.argv[1:])))
