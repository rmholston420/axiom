"""WikiGenerator — pulls a graph neighbourhood from Neo4j and synthesises a wiki page
using the local Ollama model defined in settings.

Design principles:
  - Page is anchored to a stable node ID (Query, Axiom, Source, or synthetic Topic).
  - Existing page skeleton is fetched first; only stale sections are regenerated.
  - Each generated section carries its citation URLs so pages are citation-backed.
  - Rendered markdown is stored back into Neo4j as a WikiPage node.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from neo4j import AsyncDriver

from axiom_wiki.wiki_models import WikiPage, WikiPageType, WikiSection

logger = logging.getLogger(__name__)


def _sanitize_model_output(raw: str) -> str:
    banned_patterns = [
        r"(?im)^references:\s*$",
        r"(?im)^bibliography:\s*$",
        r"(?im)^works cited:\s*$",
        r"\bJournal of [A-Z]",
        r"\bProceedings of ",
        r"\bSnow Lion Publications\b",
        r"\bHarperCollins\b",
        r"\bet al\.\b",
        r"\([12][0-9]{3}\)",
    ]
    for pattern in banned_patterns:
        if re.search(pattern, raw):
            raise ValueError(f"Generated output contains forbidden fabricated-reference pattern: {pattern}")
    return raw.strip()


# ---------------------------------------------------------------------------
# Cypher helpers
# ---------------------------------------------------------------------------

_FETCH_QUERY_NEIGHBOURHOOD = """
MATCH (q:Query {id: $id})
OPTIONAL MATCH (q)-[:HAS_FINDING]->(f:Finding)
OPTIONAL MATCH (f)-[:CITES]->(s:Source)
RETURN q, collect(DISTINCT f) AS findings, collect(DISTINCT s) AS sources
"""

_FETCH_AXIOM_NEIGHBOURHOOD = """
MATCH (a:Axiom {id: $id})
OPTIONAL MATCH (q:Query)-[:HAS_FINDING]->(f:Finding)-[:CITES]->(s:Source)
WHERE f.summary CONTAINS a.label OR f.summary CONTAINS a.statement
RETURN a, collect(DISTINCT f) AS findings, collect(DISTINCT s) AS sources
"""

_FETCH_SOURCE_NEIGHBOURHOOD = """
MATCH (s:Source {url: $id})
OPTIONAL MATCH (f:Finding)-[:CITES]->(s)
OPTIONAL MATCH (q:Query)-[:HAS_FINDING]->(f)
RETURN s, collect(DISTINCT f) AS findings, collect(DISTINCT q) AS queries
"""

_UPSERT_WIKI_PAGE = """
MERGE (w:WikiPage {page_id: $page_id})
ON CREATE SET
    w.page_type   = $page_type,
    w.title       = $title,
    w.slug        = $slug,
    w.markdown    = $markdown,
    w.content_hash = $content_hash,
    w.version     = 1,
    w.generated_at = $generated_at,
    w.created_at  = $generated_at
ON MATCH SET
    w.title       = $title,
    w.markdown    = $markdown,
    w.content_hash = $content_hash,
    w.version     = w.version + 1,
    w.generated_at = $generated_at
RETURN w.version AS version
"""

_LINK_WIKI_TO_SOURCE = """
MATCH (w:WikiPage {page_id: $page_id})
MATCH (n {id: $source_id})
MERGE (w)-[:GENERATED_FROM]->(n)
"""

_FETCH_WIKI_PAGE = """
MATCH (w:WikiPage {page_id: $page_id}) RETURN w
"""

_LIST_WIKI_PAGES = """
MATCH (w:WikiPage)
RETURN w.page_id AS page_id, w.page_type AS page_type,
       w.title AS title, w.slug AS slug,
       w.generated_at AS generated_at, w.version AS version
ORDER BY w.generated_at DESC
LIMIT $limit
"""

_DELETE_WIKI_PAGE = """
MATCH (w:WikiPage {page_id: $page_id}) DETACH DELETE w
"""


# ---------------------------------------------------------------------------
# WikiGenerator
# ---------------------------------------------------------------------------

class WikiGenerator:
    """Generates and stores wiki pages from graph data via Ollama."""

    def __init__(
        self,
        driver: AsyncDriver,
        ollama_base_url: str,
        model: str,
    ) -> None:
        self._driver = driver
        self._ollama_base_url = ollama_base_url.rstrip("/")
        self._model = model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_query_page(self, query_id: str) -> WikiPage:
        """Generate / refresh a Topic-type wiki page for a Query node."""
        data = await self._fetch_query_neighbourhood(query_id)
        query_node = data["query"]
        findings = data["findings"]
        sources = data["sources"]

        slug = self._slugify(query_node.get("text", query_id))
        title = query_node.get("text", query_id)[:120]

        sections = await self._build_query_sections(title, findings, sources)
        source_urls = [s.get("url", "") for s in sources if s.get("url")]
        related = [f.get("id", "") for f in findings if f.get("id")]

        page = self._assemble_page(
            page_id=f"query:{query_id}",
            page_type=WikiPageType.TOPIC,
            title=title,
            slug=slug,
            sections=sections,
            source_urls=source_urls,
            related_ids=related,
        )
        await self._persist(page, anchor_id=query_id)
        return page

    async def generate_axiom_page(self, axiom_id: str) -> WikiPage:
        """Generate / refresh an Axiom-type wiki page."""
        data = await self._fetch_axiom_neighbourhood(axiom_id)
        axiom_node = data["axiom"]
        findings = data["findings"]
        sources = data["sources"]

        label = axiom_node.get("label", axiom_id)
        title = f"Axiom: {label}"
        slug = self._slugify(title)

        sections = await self._build_axiom_sections(axiom_node, findings, sources)
        source_urls = [s.get("url", "") for s in sources if s.get("url")]

        page = self._assemble_page(
            page_id=f"axiom:{axiom_id}",
            page_type=WikiPageType.AXIOM,
            title=title,
            slug=slug,
            sections=sections,
            source_urls=source_urls,
        )
        await self._persist(page, anchor_id=axiom_id)
        return page

    async def generate_source_page(self, source_url: str) -> WikiPage:
        """Generate / refresh a Source-type wiki page."""
        data = await self._fetch_source_neighbourhood(source_url)
        source_node = data["source"]
        findings = data["findings"]

        title = source_node.get("title") or source_url
        slug = self._slugify(title)

        sections = await self._build_source_sections(source_node, findings)

        page = self._assemble_page(
            page_id=f"source:{self._hash_id(source_url)}",
            page_type=WikiPageType.SOURCE,
            title=f"Source: {title[:100]}",
            slug=slug,
            sections=sections,
            source_urls=[source_url],
        )
        await self._persist(page, anchor_id=source_url)
        return page

    async def get_page(self, page_id: str) -> dict[str, Any] | None:
        async with self._driver.session() as session:
            result = await session.run(_FETCH_WIKI_PAGE, page_id=page_id)
            record = await result.single()
            return None if record is None else dict(record["w"])

    async def list_pages(self, limit: int = 100) -> list[dict[str, Any]]:
        async with self._driver.session() as session:
            result = await session.run(_LIST_WIKI_PAGES, limit=limit)
            return [dict(r) async for r in result]

    async def delete_page(self, page_id: str) -> None:
        async with self._driver.session() as session:
            await session.run(_DELETE_WIKI_PAGE, page_id=page_id)

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    async def _build_query_sections(
        self,
        topic: str,
        findings: list[dict],
        sources: list[dict],
    ) -> list[WikiSection]:
        source_urls = [s.get("url", "") for s in sources if s.get("url")]
        findings_text = "\n".join(
            f"- {f.get('sub_query', '')}: {f.get('summary', '')}" for f in findings
        )
        prompt = (
            f"You are writing an evidence-grounded encyclopedia article.\n"
            f"Topic: {topic}\n\n"
            f"Evidence from research findings:\n{findings_text}\n\n"
            f"Write exactly three wiki sections: Overview, Key Findings, and Open Questions.\n"
            f"Each section must begin with ## and contain 2-4 sentences.\n"
            f"Use ONLY the evidence provided above. Do NOT use outside knowledge.\n"
            f"Do NOT invent books, papers, authors, journals, publishers, dates, or references.\n"
            f"If the evidence is insufficient, explicitly say the evidence is limited.\n"
            f"Use plain prose only. No bullet lists. No references section."
        )
        raw = await self._ollama_generate(prompt)
        return self._parse_sections(raw, source_urls)

    async def _build_axiom_sections(
        self,
        axiom: dict,
        findings: list[dict],
        sources: list[dict],
    ) -> list[WikiSection]:
        source_urls = [s.get("url", "") for s in sources if s.get("url")]
        findings_text = "\n".join(f"- {f.get('summary', '')}" for f in findings[:10])
        prompt = (
            f"You are writing an evidence-grounded encyclopedia article about an axiom.\n"
            f"Axiom label: {axiom.get('label')}\n"
            f"Statement: {axiom.get('statement')}\n"
            f"Justification: {axiom.get('justification')}\n"
            f"Confidence: {axiom.get('confidence')}\n\n"
            f"Supporting evidence:\n{findings_text}\n\n"
            f"Write exactly four wiki sections: Statement, Justification, Supporting Evidence, "
            f"Contradictions and Open Questions.\n"
            f"Each section must begin with ## and contain 2-4 sentences.\n"
            f"Use ONLY the evidence provided above. Do NOT use outside knowledge.\n"
            f"Do NOT invent books, papers, authors, journals, publishers, dates, or references.\n"
            f"If the evidence is insufficient, explicitly say the evidence is limited.\n"
            f"No bullet lists. No references section."
        )
        raw = await self._ollama_generate(prompt)
        return self._parse_sections(raw, source_urls)

    async def _build_source_sections(
        self,
        source: dict,
        findings: list[dict],
    ) -> list[WikiSection]:
        findings_text = "\n".join(f"- {f.get('summary', '')}" for f in findings[:10])
        prompt = (
            f"You are writing an evidence-grounded encyclopedia article about a source document.\n"
            f"URL: {source.get('url')}\n"
            f"Title: {source.get('title', 'Unknown')}\n\n"
            f"This source was cited in the following research findings:\n{findings_text}\n\n"
            f"Write exactly three wiki sections: About This Source, Key Contributions, Limitations.\n"
            f"Each section must begin with ## and contain 2-4 sentences.\n"
            f"Use ONLY the evidence provided above. Do NOT use outside knowledge.\n"
            f"Do NOT invent books, papers, authors, journals, publishers, dates, or references.\n"
            f"If the evidence is insufficient, explicitly say the evidence is limited.\n"
            f"No bullet lists. No references section."
        )
        raw = await self._ollama_generate(prompt)
        return self._parse_sections(raw, [source.get("url", "")])

    # ------------------------------------------------------------------
    # Ollama interface
    # ------------------------------------------------------------------

    async def _ollama_generate(self, prompt: str) -> str:
        url = f"{self._ollama_base_url}/api/generate"
        payload = {"model": self._model, "prompt": prompt, "stream": False}
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "")

    # ------------------------------------------------------------------
    # Graph queries
    # ------------------------------------------------------------------

    async def _fetch_query_neighbourhood(self, query_id: str) -> dict:
        async with self._driver.session() as session:
            result = await session.run(_FETCH_QUERY_NEIGHBOURHOOD, id=query_id)
            record = await result.single()
            if record is None:
                raise ValueError(f"Query node not found: {query_id}")
            return {
                "query": dict(record["q"]),
                "findings": [dict(f) for f in record["findings"]],
                "sources": [dict(s) for s in record["sources"]],
            }

    async def _fetch_axiom_neighbourhood(self, axiom_id: str) -> dict:
        async with self._driver.session() as session:
            result = await session.run(_FETCH_AXIOM_NEIGHBOURHOOD, id=axiom_id)
            record = await result.single()
            if record is None:
                raise ValueError(f"Axiom node not found: {axiom_id}")
            return {
                "axiom": dict(record["a"]),
                "findings": [dict(f) for f in record["findings"]],
                "sources": [dict(s) for s in record["sources"]],
            }

    async def _fetch_source_neighbourhood(self, source_url: str) -> dict:
        async with self._driver.session() as session:
            result = await session.run(_FETCH_SOURCE_NEIGHBOURHOOD, id=source_url)
            record = await result.single()
            if record is None:
                raise ValueError(f"Source node not found: {source_url}")
            return {
                "source": dict(record["s"]),
                "findings": [dict(f) for f in record["findings"]],
                "queries": [dict(q) for q in record["queries"]],
            }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _assemble_page(
        self,
        page_id: str,
        page_type: WikiPageType,
        title: str,
        slug: str,
        sections: list[WikiSection],
        source_urls: list[str],
        related_ids: list[str] | None = None,
    ) -> WikiPage:
        now = datetime.now(UTC).isoformat()
        page = WikiPage(
            page_id=page_id,
            page_type=page_type,
            title=title,
            slug=slug,
            sections=sections,
            source_urls=source_urls,
            related_ids=related_ids or [],
            generated_at=now,
        )
        md = page.to_markdown()
        page.content_hash = hashlib.sha256(md.encode()).hexdigest()
        return page

    async def _persist(self, page: WikiPage, anchor_id: str) -> None:
        md = page.to_markdown()
        async with self._driver.session() as session:
            result = await session.run(
                _UPSERT_WIKI_PAGE,
                page_id=page.page_id,
                page_type=page.page_type.value,
                title=page.title,
                slug=page.slug,
                markdown=md,
                content_hash=page.content_hash,
                generated_at=page.generated_at,
            )
            record = await result.single()
            if record:
                page.version = record["version"]
        # Link WikiPage to its anchor node (best-effort; anchor type varies)
        for node_id in [anchor_id]:
            try:
                async with self._driver.session() as session:
                    await session.run(_LINK_WIKI_TO_SOURCE, page_id=page.page_id, source_id=node_id)
            except Exception:
                pass  # anchor may not have an id property (e.g. Source uses url)

    @staticmethod
    def _slugify(text: str) -> str:
        import re
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_]+", "-", text)
        return text[:80]

    @staticmethod
    def _hash_id(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    @staticmethod
    def _parse_sections(raw: str, citation_urls: list[str]) -> list[WikiSection]:
        """Parse LLM output into WikiSection objects.

        Expects sections headed by lines beginning with '## '.
        Falls back to a single section if no headings found.
        """
        raw = _sanitize_model_output(raw)
        sections: list[WikiSection] = []
        current_heading = "Overview"
        current_lines: list[str] = []

        for line in raw.splitlines():
            if line.startswith("## "):
                if current_lines:
                    sections.append(
                        WikiSection(
                            heading=current_heading,
                            body="\n".join(current_lines).strip(),
                            citations=citation_urls,
                        )
                    )
                current_heading = line[3:].strip()
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            sections.append(
                WikiSection(
                    heading=current_heading,
                    body="\n".join(current_lines).strip(),
                    citations=citation_urls,
                )
            )

        return sections or [
            WikiSection(heading="Overview", body=raw.strip(), citations=citation_urls)
        ]
