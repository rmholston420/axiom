"""Planner breaks a top-level question into sub-queries via Ollama."""

from __future__ import annotations

import json
import re

from axiom_core.settings import settings
from axiom_providers.ollama import OllamaProvider

from .models import SubQuery


_PLAN_SYSTEM = """You are a research planner.
Given a question, output a JSON array of search sub-queries that together will answer the question comprehensively.
Return ONLY the JSON array: no explanation, no markdown fences.

Example output:
["sub-query 1", "sub-query 2", "sub-query 3"]
"""


def _normalize_question(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


def _explicit_platform_reference(question: str) -> bool:
    q = _normalize_question(question)
    markers = (
        "axiom research workbench",
        "axiom local research workbench",
        "local research workbench",
        "axiom api",
        "axiom web",
        "axiom council",
        "axiom axiomatizer",
    )
    return any(marker in q for marker in markers)


def _ambiguous_axiom_reference(question: str) -> bool:
    q = _normalize_question(question)
    return "axiom" in q and not _explicit_platform_reference(question)


def _heuristic_queries(question: str, breadth: int) -> list[str]:
    q = question.strip()
    if not q:
        return []

    normalized = _normalize_question(q)
    queries: list[str] = []

    if _explicit_platform_reference(q):
        queries.extend(
            [
                f"{q} overview",
                "Axiom Local Research Workbench overview",
                "Axiom API Axiom Web architecture",
                "Axiom Council Axiomatizer research workbench",
            ]
        )
    elif _ambiguous_axiom_reference(q):
        queries.extend(
            [
                "axiom definition philosophy",
                "axiom definition mathematics",
                "axiom meaning logic reasoning",
                "axiom computer science formal systems",
            ]
        )
    elif len(normalized.split()) <= 4:
        queries.extend(
            [
                q,
                f"{q} definition",
                f"{q} explanation",
                f"{q} examples",
            ]
        )

    if q not in queries:
        queries.insert(0, q)

    deduped: list[str] = []
    seen: set[str] = set()
    for item in queries:
        key = _normalize_question(item)
        if key and key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped[: max(1, breadth)]


class Planner:
    def __init__(self, ollama: OllamaProvider) -> None:
        self._ollama = ollama

    async def plan(self, question: str, breadth: int | None = None) -> list[SubQuery]:
        """Return up to breadth sub-queries for question."""
        n = breadth or settings.axiom_breadth
        prompt = (
            f"Generate exactly {n} search sub-queries for the following question.\n"
            f"Question: {question}"
        )
        raw = await self._ollama.generate(
            model=settings.axiom_model_planner,
            prompt=prompt,
            system=_PLAN_SYSTEM,
        )
        model_queries = _parse_json_list(raw)
        if model_queries:
            return [SubQuery(text=sq, depth=0) for sq in model_queries[:n]]

        fallback_queries = _heuristic_queries(question, n)
        return [SubQuery(text=sq, depth=0) for sq in fallback_queries[:n]]


def _parse_json_list(text: str) -> list[str]:
    """Extract the first JSON array from text, tolerating markdown fences."""
    cleaned = re.sub(r"```[\w]*", "", text).strip()
    m = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if m:
        try:
            result = json.loads(m.group(0))
            if isinstance(result, list):
                return [str(item) for item in result]
        except json.JSONDecodeError:
            pass
    return [line.strip().strip("-").strip('"') for line in cleaned.splitlines() if line.strip()]
