"""Research-specific Pydantic models."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SubQuery(BaseModel):
    text: str
    depth: int = 0


class RawFinding(BaseModel):
    sub_query: str
    summary: str
    source_urls: list[str] = Field(default_factory=list)


class ResearchResult(BaseModel):
    query: str
    query_id: str
    findings: list[RawFinding] = Field(default_factory=list)
    report: str = ""
