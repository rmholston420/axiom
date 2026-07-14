"""Axiomatizer endpoint — propose, evaluate, and persist an Axiom node in Neo4j."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from neo4j import AsyncGraphDatabase

from axiom_core.settings import settings
from axiom_providers.ollama import OllamaProvider

log = logging.getLogger(__name__)

router = APIRouter(prefix="/axiomatizer", tags=["axiomatizer"])

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AxiomRequest(BaseModel):
    """A transform request: source_text is the content to axiomatize."""
    source_text: str = Field(..., min_length=10, description="The text or finding to transform into an axiom.")
    context: str = Field(default="", description="Optional extra context for the model.")
    label: str = Field(default="", description="Optional human label for this axiom.")


class AxiomResponse(BaseModel):
    axiom_id: str
    label: str
    statement: str
    justification: str
    confidence: float
    created_at: str
    persisted: bool


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_SYSTEM_PROPOSE = (
    "You are the Axiom Axiomatizer. Your job is to distill a piece of research text into a "
    "precise, falsifiable axiomatic statement — a claim that could serve as a foundational "
    "principle for future reasoning. "
    "Respond in this exact JSON format (no markdown fences, no extra keys):\n"
    "{\n"
    '  "statement": "<one-sentence axiom>",\n'
    '  "justification": "<1-3 sentences explaining why this axiom holds>",\n'
    '  "confidence": <float 0.0–1.0>\n'
    "}"
)

_SYSTEM_EVALUATE = (
    "You are a rigorous evaluator of axiomatic statements. "
    "Given an axiom statement and its justification, decide whether it is "
    "well-formed, non-trivial, and falsifiable. "
    "Respond with a single JSON object:\n"
    '{"approved": true|false, "reason": "<brief reason>"}'
)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

async def _propose_axiom(ollama: OllamaProvider, source_text: str, context: str) -> dict:
    """Ask the axiomatizer model to propose an axiom from source_text."""
    prompt = f"Source text:\n{source_text}"
    if context:
        prompt += f"\n\nAdditional context:\n{context}"

    raw = await ollama.generate(
        model=settings.axiom_model_axiomatizer,
        prompt=prompt,
        system=_SYSTEM_PROPOSE,
    )

    import json
    try:
        # Strip any accidental markdown fences
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError) as exc:
        log.warning("Axiomatizer propose parse error: %s — raw: %.200s", exc, raw)
        raise HTTPException(
            status_code=502,
            detail=f"Axiomatizer model returned unparseable JSON: {raw[:300]}",
        )


async def _evaluate_axiom(ollama: OllamaProvider, statement: str, justification: str) -> dict:
    """Ask the critic model to evaluate the proposed axiom."""
    import json
    prompt = f'Axiom: "{statement}"\nJustification: "{justification}"'
    raw = await ollama.generate(
        model=settings.axiom_model_critic,
        prompt=prompt,
        system=_SYSTEM_EVALUATE,
    )
    try:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        log.warning("Axiomatizer evaluate parse error — raw: %.200s", raw)
        # Fail open: treat as approved so the axiom still persists
        return {"approved": True, "reason": "evaluation parse failed — defaulting to approved"}


async def _persist_axiom(
    axiom_id: str,
    label: str,
    statement: str,
    justification: str,
    confidence: float,
    approved: bool,
    eval_reason: str,
    created_at: str,
) -> None:
    """Write an Axiom node to Neo4j."""
    driver = AsyncGraphDatabase.driver(
        settings.axiom_neo4j_uri,
        auth=(settings.axiom_neo4j_user, settings.axiom_neo4j_password),
    )
    cypher = """
    MERGE (a:Axiom {id: $id})
    ON CREATE SET
        a.label        = $label,
        a.statement    = $statement,
        a.justification = $justification,
        a.confidence   = $confidence,
        a.approved     = $approved,
        a.eval_reason  = $eval_reason,
        a.created_at   = $created_at
    ON MATCH SET
        a.statement    = $statement,
        a.justification = $justification,
        a.confidence   = $confidence,
        a.approved     = $approved,
        a.eval_reason  = $eval_reason
    RETURN a.id AS id
    """
    try:
        async with driver.session() as session:
            await session.run(
                cypher,
                id=axiom_id,
                label=label,
                statement=statement,
                justification=justification,
                confidence=float(confidence),
                approved=approved,
                eval_reason=eval_reason,
                created_at=created_at,
            )
    finally:
        await driver.close()


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("", response_model=AxiomResponse)
async def run_axiomatizer(body: AxiomRequest) -> AxiomResponse:
    """Propose an axiom from source_text, evaluate it, then persist it in Neo4j.

    Guarded by AXIOM_AXIOMATIZER_ENABLED feature toggle.
    """
    if not settings.axiom_axiomatizer_enabled:
        raise HTTPException(
            status_code=503,
            detail="Axiomatizer is disabled. Set AXIOM_AXIOMATIZER_ENABLED=true to enable.",
        )

    ollama = OllamaProvider()
    created_at = datetime.now(timezone.utc).isoformat()
    axiom_id = str(uuid.uuid4())

    # 1. Propose
    proposal = await _propose_axiom(ollama, body.source_text, body.context)
    statement: str = proposal.get("statement", "").strip()
    justification: str = proposal.get("justification", "").strip()
    confidence: float = float(proposal.get("confidence", 0.5))

    if not statement:
        raise HTTPException(status_code=502, detail="Axiomatizer returned an empty statement.")

    # 2. Evaluate
    evaluation = await _evaluate_axiom(ollama, statement, justification)
    approved: bool = bool(evaluation.get("approved", True))
    eval_reason: str = evaluation.get("reason", "")

    log.info(
        "Axiom %s | approved=%s | confidence=%.2f | %.80s",
        axiom_id, approved, confidence, statement,
    )

    # 3. Persist regardless of approval (approved flag is recorded on the node)
    await _persist_axiom(
        axiom_id=axiom_id,
        label=body.label or statement[:60],
        statement=statement,
        justification=justification,
        confidence=confidence,
        approved=approved,
        eval_reason=eval_reason,
        created_at=created_at,
    )

    return AxiomResponse(
        axiom_id=axiom_id,
        label=body.label or statement[:60],
        statement=statement,
        justification=justification,
        confidence=confidence,
        created_at=created_at,
        persisted=True,
    )


@router.get("/axioms", response_model=list[AxiomResponse])
async def list_axioms(limit: int = 50) -> list[AxiomResponse]:
    """Return up to `limit` Axiom nodes from Neo4j, newest first."""
    if not settings.axiom_axiomatizer_enabled:
        raise HTTPException(status_code=503, detail="Axiomatizer is disabled.")

    driver = AsyncGraphDatabase.driver(
        settings.axiom_neo4j_uri,
        auth=(settings.axiom_neo4j_user, settings.axiom_neo4j_password),
    )
    cypher = """
    MATCH (a:Axiom)
    RETURN a
    ORDER BY a.created_at DESC
    LIMIT $limit
    """
    try:
        async with driver.session() as session:
            result = await session.run(cypher, limit=limit)
            rows = [dict(r["a"]) async for r in result]
    finally:
        await driver.close()

    return [
        AxiomResponse(
            axiom_id=r["id"],
            label=r.get("label", ""),
            statement=r.get("statement", ""),
            justification=r.get("justification", ""),
            confidence=float(r.get("confidence", 0.5)),
            created_at=r.get("created_at", ""),
            persisted=True,
        )
        for r in rows
    ]
