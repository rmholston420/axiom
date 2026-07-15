"""ResearchLoop — orchestrates planner → retriever → extractor → graph → synthesizer."""

from __future__ import annotations

from neo4j import AsyncDriver

from axiom_graph.repository import GraphRepository
from axiom_graph.schema import ensure_schema
from axiom_providers.ollama import OllamaProvider
from axiom_providers.searxng import SearxngProvider

from .extractor import Extractor
from .models import RawFinding, ResearchResult
from .planner import Planner
from .retriever import Retriever
from .synthesizer import Synthesizer


class ResearchLoop:
    """Full research pipeline for a single question."""

    def __init__(self, driver: AsyncDriver) -> None:
        self._driver = driver
        self._ollama = OllamaProvider()
        self._searxng = SearxngProvider()
        self._planner = Planner(self._ollama)
        self._retriever = Retriever(self._searxng)
        self._extractor = Extractor(self._ollama)
        self._synthesizer = Synthesizer(self._ollama)

    async def run(
        self,
        question: str,
        job_id: str | None = None,
        breadth: int | None = None,
    ) -> ResearchResult:
        """Run the full loop and return a ResearchResult."""
        # Bootstrap schema on first run (idempotent)
        await ensure_schema(self._driver)

        repo = GraphRepository(self._driver)
        query_id = await repo.create_query(question, job_id=job_id)

        # Plan
        sub_queries = await self._planner.plan(question, breadth=breadth)

        findings: list[RawFinding] = []
        for sq in sub_queries:
            # Retrieve
            results = await self._retriever.retrieve(sq.text)

            # Upsert sources into graph
            source_urls = []
            for r in results:
                await repo.upsert_source(url=r.url, title=r.title)
                source_urls.append(r.url)

            # Extract summary
            summary = await self._extractor.extract(sq.text, results)

            # Persist Finding
            await repo.create_finding(
                query_id=query_id,
                sub_query=sq.text,
                summary=summary,
                source_urls=source_urls,
            )

            findings.append(RawFinding(sub_query=sq.text, summary=summary, source_urls=source_urls))

        # Synthesize final report
        report = await self._synthesizer.synthesize(question, findings)

        return ResearchResult(
            query=question,
            query_id=query_id,
            findings=findings,
            report=report,
        )
