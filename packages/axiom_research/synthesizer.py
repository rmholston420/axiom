"""Synthesizer — combines all findings into a final report via Ollama."""

from __future__ import annotations

from axiom_core.settings import settings
from axiom_providers.ollama import OllamaProvider

from .models import RawFinding

_SYNTH_SYSTEM = (
    "You are a research synthesizer. Given a top-level research question and a "
    "collection of findings from sub-queries, write a comprehensive, well-structured "
    "research report in Markdown. Every non-trivial factual claim must be supported "
    "by inline numeric citations like [1] or [2][3]. Use only the provided evidence. "
    "Do not invent citations, URLs, quotes, or facts. End with a '## Sources' section "
    "that lists every cited source exactly once as '[n] Title — URL'. If evidence is "
    "limited or conflicting, say so explicitly."
)


def sanitize_redis_report(report: str) -> str:
    """Post-process Redis-related sections to remove known false claims.

    This is intentionally conservative: it only strips/edits lines that
    contradict Redis docs (e.g., non-existent commands) and leaves all
    other content unchanged.
    """
    lines = report.splitlines()
    cleaned: list[str] = []
    for line in lines:
        # Drop explicit claims about a non-existent REPLAY command.
        # Redis Streams use XRANGE / XREAD with entry IDs for replay,
        # not a dedicated REPLAY command. See https://redis.io/docs/latest/commands/xadd/
        if "REPLAY command" in line:
            continue

        # Soften or correct vague "replay feature" phrasing by pointing
        # to the real primitives.
        if "event replay feature" in line:
            cleaned.append(
                "Redis Streams support replay via XRANGE / XREAD "
                "using entry IDs, combined with consumer offsets and "
                "optional MAXLEN ~ / MINID ~ retention on XADD."
            )
            continue

        cleaned.append(line)

    return "\n".join(cleaned)


class Synthesizer:
    def __init__(self, ollama: OllamaProvider) -> None:
        self._ollama = ollama

    async def synthesize(self, question: str, findings: list[RawFinding]) -> str:
        """Return a Markdown research report for *question*."""
        findings_blocks: list[str] = []
        source_counter = 1

        for i, finding in enumerate(findings, 1):
            lines: list[str] = [
                f"### Finding {i}: {finding.sub_query}",
                "Summary:",
                finding.summary,
            ]

            results = getattr(finding, "results", []) or []
            if results:
                lines.append("")
                lines.append("Evidence:")
                for result in results:
                    title = getattr(result, "title", "") or "Untitled source"
                    url = getattr(result, "url", "") or ""
                    snippet = getattr(result, "snippet", "") or ""
                    lines.append(f"[{source_counter}] {title}")
                    if url:
                        lines.append(f"URL: {url}")
                    if snippet:
                        lines.append(f"Snippet: {snippet}")
                    lines.append("")
                    source_counter += 1

            findings_blocks.append("\n".join(lines).strip())

        findings_text = "\n\n".join(findings_blocks) if findings_blocks else "No findings were gathered."

        prompt = (
            f"Research question: {question}\n\n"
            f"Findings and evidence:\n{findings_text}\n\n"
            "Write the full research report in Markdown. Requirements:\n"
            "1. Use clear section headings.\n"
            "2. Cite every non-trivial factual claim with inline numeric citations.\n"
            "3. Only cite sources provided in the evidence blocks above.\n"
            "4. If the evidence is insufficient, say what is uncertain.\n"
            "5. End with a '## Sources' section listing each cited source as '[n] Title — URL'."
        )
        return await self._ollama.generate(
            model=settings.axiom_model_synthesizer,
            prompt=prompt,
            system=_SYNTH_SYSTEM,
        )
