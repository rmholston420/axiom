"""Council endpoint — fan-out to N members then synthesize to consensus/disagreement."""
from __future__ import annotations

import asyncio
import logging
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from axiom_core.settings import settings
from axiom_providers.ollama import OllamaProvider

log = logging.getLogger(__name__)

router = APIRouter(prefix="/council", tags=["council"])

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CouncilRequest(BaseModel):
    question: str
    context: str = ""
    council_size: int = Field(default=0, ge=0, le=10)
    mode: Literal["sequential", "parallel"] = "sequential"


class MemberOpinion(BaseModel):
    member_id: int
    role: str
    opinion: str


class CouncilResponse(BaseModel):
    question: str
    mode: str
    members: list[MemberOpinion]
    consensus: str
    has_disagreement: bool
    chairman_synthesis: str


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_MEMBER_SYSTEM = (
    "You are council member {role}. You are a careful, critical thinker. "
    "Given a research question and supporting context, give your honest, "
    "concise opinion in 2-4 sentences. If you disagree with a common view, say so."
)

_CHAIRMAN_SYSTEM = (
    "You are the Chairman of the Axiom Council. "
    "You have received independent opinions from {n} council members on a research question. "
    "Synthesize their views into a final council response. "
    "If members agree, state the consensus clearly. "
    "If members disagree on key points, highlight the disagreement and note both perspectives. "
    "Be precise and concise. Output in Markdown."
)

_ROLES = [
    "Analyst",
    "Critic",
    "Synthesizer",
    "Devil's Advocate",
    "Domain Expert",
    "Skeptic",
    "Integrator",
    "Ethicist",
    "Strategist",
    "Visionary",
]


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

async def _get_member_opinion(
    ollama: OllamaProvider,
    member_id: int,
    role: str,
    question: str,
    context: str,
) -> MemberOpinion:
    """Ask one council member for their opinion."""
    prompt = f"Research question: {question}"
    if context:
        prompt += f"\n\nContext:\n{context}"

    system = _MEMBER_SYSTEM.format(role=role)
    opinion = await ollama.generate(
        model=settings.axiom_model_critic,
        prompt=prompt,
        system=system,
    )
    return MemberOpinion(member_id=member_id, role=role, opinion=opinion.strip())


async def _chairman_synthesize(
    ollama: OllamaProvider,
    question: str,
    opinions: list[MemberOpinion],
) -> str:
    """Chairman reads all opinions and returns a synthesis."""
    opinions_text = "\n\n".join(
        f"**Member {o.member_id} ({o.role}):**\n{o.opinion}" for o in opinions
    )
    prompt = (
        f"Research question: {question}\n\n"
        f"Council opinions:\n\n{opinions_text}\n\n"
        "Provide your synthesis."
    )
    system = _CHAIRMAN_SYSTEM.format(n=len(opinions))
    return await ollama.generate(
        model=settings.axiom_model_chairman,
        prompt=prompt,
        system=system,
    )


def _detect_disagreement(opinions: list[MemberOpinion]) -> bool:
    """Heuristic: look for disagreement signal words in any opinion."""
    signals = [
        "disagree", "however", "contrary", "on the other hand",
        "i would argue", "in contrast", "nevertheless", "yet",
        "dispute", "challenge", "differ",
    ]
    for o in opinions:
        lower = o.opinion.lower()
        if any(s in lower for s in signals):
            return True
    return False


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("", response_model=CouncilResponse)
async def run_council(body: CouncilRequest) -> CouncilResponse:
    """Fan-out to N council members then synthesize.

    Mode ``sequential`` (default, VRAM-safe): members queried one at a time so
    only one model call is in-flight at once — safe on 16 GB VRAM.
    Mode ``parallel``: all members queried concurrently; faster but heavier.
    """
    if not settings.axiom_council_enabled:
        raise HTTPException(status_code=503, detail="Council is disabled via AXIOM_COUNCIL_ENABLED")

    size = body.council_size if body.council_size > 0 else settings.axiom_council_size
    size = min(size, len(_ROLES))
    roles = _ROLES[:size]

    ollama = OllamaProvider()

    # --- Member fan-out ---
    if body.mode == "parallel":
        opinions: list[MemberOpinion] = await asyncio.gather(
            *[
                _get_member_opinion(ollama, i + 1, role, body.question, body.context)
                for i, role in enumerate(roles)
            ]
        )
    else:  # sequential — VRAM-safe default
        opinions = []
        for i, role in enumerate(roles):
            op = await _get_member_opinion(ollama, i + 1, role, body.question, body.context)
            opinions.append(op)
            log.info("Council member %d/%d (%s) complete", i + 1, size, role)

    has_disagreement = _detect_disagreement(opinions)

    # Build simple consensus string (first-pass agreement summary)
    consensus = (
        "Members reached broad consensus."
        if not has_disagreement
        else "Members showed notable disagreement on one or more points."
    )

    # --- Chairman synthesis ---
    chairman_synthesis = await _chairman_synthesize(ollama, body.question, opinions)

    return CouncilResponse(
        question=body.question,
        mode=body.mode,
        members=opinions,
        consensus=consensus,
        has_disagreement=has_disagreement,
        chairman_synthesis=chairman_synthesis.strip(),
    )
