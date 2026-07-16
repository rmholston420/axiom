"""Pydantic models for WikiPage and related data."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WikiPageType(str, Enum):
    TOPIC = "topic"
    ENTITY = "entity"
    SOURCE = "source"
    AXIOM = "axiom"


class WikiSection(BaseModel):
    heading: str
    body: str
    citations: list[str] = Field(default_factory=list)  # source URLs


class WikiPage(BaseModel):
    """Represents one generated wiki page anchored to a stable entity/topic ID."""

    page_id: str
    page_type: WikiPageType
    title: str
    slug: str  # URL-safe stable identifier
    summary: str = ""
    sections: list[WikiSection] = Field(default_factory=list)
    related_ids: list[str] = Field(default_factory=list)  # neighbour node IDs
    tags: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    generated_at: str = ""
    version: int = 1
    content_hash: str = ""  # sha256 of rendered markdown for diff-detection

    def to_markdown(self) -> str:
        """Render the page to GitHub-Flavored Markdown."""
        lines: list[str] = [f"# {self.title}\n"]
        if self.summary:
            lines.append(f"{self.summary}\n")
        for section in self.sections:
            lines.append(f"## {section.heading}\n")
            lines.append(section.body)
            if section.citations:
                refs = "  ".join(f"[{i+1}]({u})" for i, u in enumerate(section.citations))
                lines.append(f"\n**Sources:** {refs}\n")
        if self.related_ids:
            lines.append("## Related\n")
            lines.append(", ".join(f"`{rid}`" for rid in self.related_ids))
        lines.append(f"\n---\n*Generated: {self.generated_at} · v{self.version}*\n")
        return "\n".join(lines)


class WikiPageStub(BaseModel):
    """Lightweight representation returned by list endpoints."""

    page_id: str
    page_type: WikiPageType
    title: str
    slug: str
    generated_at: str
    version: int
