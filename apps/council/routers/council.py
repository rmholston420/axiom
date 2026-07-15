"""Council endpoint — fan-out to N members then synthesize to consensus/disagreement."""

from __future__ import annotations

import asyncio
import logging
import re
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

_MEMBER_ROLES = [
    "critical analyst",
    "domain expert",
    "devil's advocate",
    "synthesizer",
    "ethicist",
    "pragmatist",
    "historian",
    "futurist",
    "skeptic",
    "optimist",
]

_MEMBER_SYSTEM = (
    "You are a {role} on a research council. "
    "Given a question and optional context, provide a concise, well-reasoned opinion "
    "(2-4 paragraphs). Be specific and avoid generic platitudes."
)

_CHAIRMAN_SYSTEM = (
    "You are the Chairman of a research council. "
    "Given a question and opinions from multiple council members, "
    "synthesize the key points of agreement and disagreement into a coherent summary. "
    "Identify the strongest arguments, note areas of contention, and provide a "
    "balanced conclusion. Be concise and precise."
)


async def _get_member_opinion(
    ollama: OllamaProvider,
    member_id: int,
    role: str,
    question: str,
    context: str,
    model: str,
) -> MemberOpinion:
    system = _MEMBER_SYSTEM.format(role=role)
    prompt = f"Question: {question}"
    if context:
        prompt += f"\n\nContext:\n{context}"
    opinion = await ollama.generate(model=model, prompt=prompt, system=system)
    return MemberOpinion(member_id=member_id, role=role, opinion=opinion)


async def _get_chairman_synthesis(
    ollama: OllamaProvider,
    question: str,
    opinions: list[MemberOpinion],
    model: str,
) -> str:
    opinions_text = "\n\n".join(
        f"[Member {o.member_id} — {o.role}]:\n{o.opinion}" for o in opinions
    )
    prompt = f"Question: {question}\n\nCouncil Opinions:\n{opinions_text}"
    return await ollama.generate(model=model, prompt=prompt, system=_CHAIRMAN_SYSTEM)


def _detect_disagreement(opinions: list[MemberOpinion]) -> bool:
    """Heuristic: flag disagreement when opposing-sentiment markers appear."""
    disagree_markers = re.compile(
        r"\b(however|disagree|contrary|on the other hand|in contrast|"
        r"alternatively|but|yet|nevertheless|despite|challenge|refute)"
        r"\b",
        re.IGNORECASE,
    )
    combined = " ".join(o.opinion for o in opinions)
    matches = disagree_markers.findall(combined)
    return len(matches) >= 2


@router.post("", response_model=CouncilResponse)
async def run_council(body: CouncilRequest) -> CouncilResponse:
    """Run a council fan-out for the given question."""
    if not settings.axiom_council_enabled:
        raise HTTPException(
            status_code=503,
            detail="Council is disabled via AXIOM_COUNCIL_ENABLED",
        )

    size = body.council_size if body.council_size > 0 else settings.axiom_council_size
    size = max(1, min(size, len(_MEMBER_ROLES)))
    roles = _MEMBER_ROLES[:size]

    ollama = OllamaProvider()
    chairman_model = settings.axiom_model_chairman

    if body.mode == "parallel":
        opinions: list[MemberOpinion] = await asyncio.gather(
            *[
                _get_member_opinion(
                    ollama=ollama,
                    member_id=i + 1,
                    role=role,
                    question=body.question,
                    context=body.context,
                    model=chairman_model,
                )
                for i, role in enumerate(roles)
            ]
        )
    else:
        opinions = []
        for i, role in enumerate(roles):
            op = await _get_member_opinion(
                ollama=ollama,
                member_id=i + 1,
                role=role,
                question=body.question,
                context=body.context,
                model=chairman_model,
            )
            opinions.append(op)

    has_disagreement = _detect_disagreement(opinions)
    chairman_synthesis = await _get_chairman_synthesis(
        ollama=ollama,
        question=body.question,
        opinions=opinions,
        model=chairman_model,
    )

    consensus = "Agreement" if not has_disagreement else "Disagreement detected"

    return CouncilResponse(
        question=body.question,
        mode=body.mode,
        members=opinions,
        consensus=consensus,
        has_disagreement=has_disagreement,
        chairman_synthesis=chairman_synthesis,
    )
