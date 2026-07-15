"""Synthesizer — combines all findings into a final report via Ollama."""

from __future__ import annotations

from axiom_core.settings import settings
from axiom_providers.ollama import OllamaProvider

from .models import RawFinding

_SYNTH_SYSTEM = (
    "You are a research synthesizer. Given a top-level research question and a"
    " collection of findings from sub-queries, write a comprehensive, well-structured"
    " research report in Markdown. Use headings, bullet points where appropriate, and"
    " cite findings by their sub-query label. Be factual and concise."
)


class Synthesizer:
    def __init__(self, ollama: OllamaProvider) -> None:
        self._ollama = ollama

    async def synthesize(self, question: str, findings: list[RawFinding]) -> str:
        """Return a Markdown research report for *question*."""
        findings_text = "\n\n".join(
            f"### {i + 1}. {f.sub_query}\n{f.summary}" for i, f in enumerate(findings)
        )
        prompt = (
            f"Research question: {question}\n\n"
            f"Findings:\n{findings_text}\n\n"
            "Write the full research report."
        )
        return await self._ollama.generate(
            model=settings.axiom_model_synthesizer,
            prompt=prompt,
            system=_SYNTH_SYSTEM,
        )
