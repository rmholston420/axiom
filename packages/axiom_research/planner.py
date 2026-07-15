"""Planner — breaks a top-level question into sub-queries via Ollama."""

from __future__ import annotations

import json
import re

from axiom_core.settings import settings
from axiom_providers.ollama import OllamaProvider

from .models import SubQuery

_PLAN_SYSTEM = """You are a research planner. Given a question, output a JSON array
of search sub-queries that together will answer the question comprehensively.
Return ONLY the JSON array — no explanation, no markdown fences.
Example output: ["sub-query 1", "sub-query 2", "sub-query 3"]"""


class Planner:
    def __init__(self, ollama: OllamaProvider) -> None:
        self._ollama = ollama

    async def plan(self, question: str, breadth: int | None = None) -> list[SubQuery]:
        """Return up to *breadth* sub-queries for *question*."""
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
        sub_queries = _parse_json_list(raw)
        return [SubQuery(text=sq, depth=0) for sq in sub_queries[:n]]


def _parse_json_list(text: str) -> list[str]:
    """Extract the first JSON array from *text*, tolerating markdown fences."""
    # Strip markdown code fences if present
    cleaned = re.sub(r"```[\w]*", "", text).strip()
    # Find the outermost [...]
    m = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if m:
        try:
            result = json.loads(m.group())
            if isinstance(result, list):
                return [str(item) for item in result]
        except json.JSONDecodeError:
            pass
    # Fallback: return any non-empty lines as queries
    return [line.strip().strip('"').strip("'") for line in cleaned.splitlines() if line.strip()]
