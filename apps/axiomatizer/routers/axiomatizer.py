"""Axiomatizer endpoint — propose, evaluate, and persist an Axiom node in Neo4j."""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from neo4j import AsyncGraphDatabase
from pydantic import BaseModel, Field

from axiom_core.settings import settings
from axiom_providers.ollama import OllamaProvider

log = logging.getLogger(__name__)

router = APIRouter(prefix="/axiomatizer", tags=["axiomatizer"])


class AxiomRequest(BaseModel):
    source_text: str = Field(..., min_length=10)
    context: str = ""
    label: str = ""


class AxiomResponse(BaseModel):
    axiom_id: str
    label: str
    statement: str
    justification: str
    confidence: float
    created_at: str
    persisted: bool


_SYSTEM_PROPOSE = (
    "You are the Axiom Axiomatizer. Distill the input into a precise, falsifiable axiom. "
    "Return strict JSON only with keys statement, justification, confidence. "
    "confidence must be a number from 0.0 to 1.0."
)

_SYSTEM_EVALUATE = (
    "You are a rigorous evaluator of axiomatic statements. "
    "Evaluate whether the axiom is well-formed, non-trivial, and falsifiable. "
    "Return strict JSON only with keys approved and reason. "
    "approved must be true or false."
)


def _extract_json_object(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```json"):
        text = text[len("```json"):].strip()
    elif text.startswith("```"):
        text = text[len("```"):].strip()
    if text.endswith("```"):
        text = text[:-3].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


async def _propose_axiom(ollama: OllamaProvider, source_text: str, context: str) -> dict:
    prompt = f"Source text:\n{source_text}"
    if context:
        prompt += f"\n\nAdditional context:\n{context}"
    raw = await ollama.generate(
        model=settings.axiom_model_axiomatizer,
        prompt=prompt,
        system=_SYSTEM_PROPOSE,
    )
    try:
        data = _extract_json_object(raw)
        return {
            "statement": str(data.get("statement", "")).strip(),
            "justification": str(data.get("justification", "")).strip(),
            "confidence": float(data.get("confidence", 0.5)),
        }
    except Exception as exc:
        log.warning("Axiomatizer propose parse error: %s | raw=%r", exc, raw[:500])
        raise HTTPException(status_code=502, detail=f"Unparseable axiomatizer JSON: {raw[:300]}")


async def _evaluate_axiom(ollama: OllamaProvider, statement: str, justification: str) -> dict:
    prompt = (
        "Axiom statement:\n"
        f"{statement}\n\n"
        "Justification:\n"
        f"{justification}\n\n"
        "Return JSON only."
    )
    raw = await ollama.generate(
        model=settings.axiom_model_critic,
        prompt=prompt,
        system=_SYSTEM_EVALUATE,
    )
    try:
        data = _extract_json_object(raw)
        return {
            "approved": bool(data.get("approved", True)),
            "reason": str(data.get("reason", "")).strip(),
        }
    except Exception as exc:
        log.warning("Axiomatizer evaluate parse error: %s | raw=%r", exc, raw[:500])
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
    driver = AsyncGraphDatabase.driver(
        settings.axiom_neo4j_uri,
        auth=(settings.axiom_neo4j_user, settings.axiom_neo4j_password),
    )
    cypher = """
    MERGE (a:Axiom {id: $id})
    ON CREATE SET
        a.label = $label,
        a.statement = $statement,
        a.justification = $justification,
        a.confidence = $confidence,
        a.approved = $approved,
        a.eval_reason = $eval_reason,
        a.created_at = $created_at
    ON MATCH SET
        a.label = $label,
        a.statement = $statement,
        a.justification = $justification,
        a.confidence = $confidence,
        a.approved = $approved,
        a.eval_reason = $eval_reason
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


@router.post("", response_model=AxiomResponse)
async def run_axiomatizer(body: AxiomRequest) -> AxiomResponse:
    if not settings.axiom_axiomatizer_enabled:
        raise HTTPException(status_code=503, detail="Axiomatizer is disabled. Set AXIOM_AXIOMATIZER_ENABLED=true to enable.")

    ollama = OllamaProvider()
    created_at = datetime.now(timezone.utc).isoformat()
    axiom_id = str(uuid.uuid4())

    proposal = await _propose_axiom(ollama, body.source_text, body.context)
    statement = proposal["statement"]
    justification = proposal["justification"]
    confidence = proposal["confidence"]

    if not statement:
        raise HTTPException(status_code=502, detail="Axiomatizer returned an empty statement.")

    evaluation = await _evaluate_axiom(ollama, statement, justification)
    approved = evaluation["approved"]
    eval_reason = evaluation["reason"]

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


@router.get("/axioms")
async def list_axioms(limit: int = 50):
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
    return rows
