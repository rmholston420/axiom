"""Axiomatizer endpoint — propose, evaluate, and persist Axiom nodes in Neo4j."""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from neo4j import AsyncDriver, AsyncGraphDatabase
from pydantic import BaseModel, Field

from axiom_core.settings import settings
from axiom_providers.ollama import OllamaProvider

log = logging.getLogger(__name__)

router = APIRouter(prefix="/axiomatizer", tags=["axiomatizer"])


class AxiomRequest(BaseModel):
    source_text: str = Field(..., min_length=10)
    context: str = ""
    label: str = ""


class ProposedAxiom(BaseModel):
    statement: str
    justification: str
    confidence: float = 0.5


class AxiomResponse(BaseModel):
    axiom_id: str
    label: str
    statement: str
    justification: str
    confidence: float
    approved: bool
    eval_reason: str = ""
    evaluation_warning: bool = False
    created_at: str
    persisted: bool


_SYSTEM_PROPOSE = (
    "You are the Axiom Axiomatizer. Distill the input into 3 to 7 precise, distinct, falsifiable axioms. "
    "Return strict JSON only with one top-level key axioms. "
    "axioms must be an array of objects, and each object must contain keys statement, justification, confidence. "
    "confidence must be a number from 0.0 to 1.0. "
    "Avoid duplicates, near-duplicates, vague summaries, and trivial restatements."
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


def _coerce_axiom_list(data: dict) -> list[dict]:
    items = data.get("axioms")
    if not isinstance(items, list):
        single_statement = str(data.get("statement", "")).strip()
        if single_statement:
            items = [data]
        else:
            items = []

    axioms: list[dict] = []
    seen: set[str] = set()

    for item in items:
        if not isinstance(item, dict):
            continue
        statement = str(item.get("statement", "")).strip()
        justification = str(item.get("justification", "")).strip()
        if not statement:
            continue
        key = statement.casefold()
        if key in seen:
            continue
        seen.add(key)
        try:
            confidence = float(item.get("confidence", 0.5))
        except Exception:
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))
        axioms.append(
            {
                "statement": statement,
                "justification": justification,
                "confidence": confidence,
            }
        )

    return axioms


async def _propose_axioms(ollama: OllamaProvider, source_text: str, context: str) -> list[dict]:
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
        axioms = _coerce_axiom_list(data)
        if not axioms:
            raise ValueError("No valid axioms returned")
        return axioms
    except Exception as exc:
        log.warning("Axiomatizer propose parse error: %s | raw=%r", exc, raw[:500])
        raise HTTPException(status_code=502, detail=f"Unparseable axiomatizer JSON: {raw[:300]}")


async def _evaluate_axiom(ollama: OllamaProvider, statement: str, justification: str) -> dict:
    prompt = (
        f"Axiom statement:\n{statement}\n\nJustification:\n{justification}\n\nReturn JSON only."
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
            "evaluation_warning": False,
        }
    except Exception as exc:
        log.warning("Axiomatizer evaluate parse error: %s | raw=%r", exc, raw[:500])
        return {
            "approved": True,
            "reason": "Model evaluation failed, treating as approved",
            "evaluation_warning": True,
        }


async def _get_driver(request: Optional[Request]) -> tuple[AsyncDriver, bool]:
    """Return (driver, should_close). Re-uses the lifespan driver when available."""
    if request is not None:
        state = getattr(request.app, "state", None)
        driver = getattr(state, "driver", None) if state else None
        if driver is not None:
            return driver, False
    driver = AsyncGraphDatabase.driver(
        settings.axiom_neo4j_uri,
        auth=(settings.axiom_neo4j_user, settings.axiom_neo4j_password),
    )
    return driver, True


@router.post("", response_model=list[AxiomResponse])
async def run_axiomatizer(body: AxiomRequest, request: Request) -> list[AxiomResponse]:
    if not settings.axiom_axiomatizer_enabled:
        raise HTTPException(
            status_code=503,
            detail="Axiomatizer is disabled. Set AXIOM_AXIOMATIZER_ENABLED=true to enable.",
        )

    ollama = OllamaProvider()
    created_at = datetime.now(UTC).isoformat()
    proposals = await _propose_axioms(ollama, body.source_text, body.context)
    if not proposals:
        raise HTTPException(status_code=502, detail="No valid axioms returned by model")

    driver, should_close = await _get_driver(request)
    cypher = """
    MERGE (a:Axiom {id: $id})
    ON CREATE SET
        a.label = $label,
        a.statement = $statement,
        a.justification = $justification,
        a.confidence = $confidence,
        a.approved = $approved,
        a.eval_reason = $eval_reason,
        a.evaluation_warning = $evaluation_warning,
        a.created_at = $created_at
    ON MATCH SET
        a.label = $label,
        a.statement = $statement,
        a.justification = $justification,
        a.confidence = $confidence,
        a.approved = $approved,
        a.eval_reason = $eval_reason,
        a.evaluation_warning = $evaluation_warning
    RETURN a.id AS id
    """

    responses: list[AxiomResponse] = []
    try:
        async with driver.session() as session:
            for idx, proposal in enumerate(proposals, start=1):
                statement = proposal["statement"]
                justification = proposal["justification"]
                confidence = float(proposal["confidence"])

                evaluation = await _evaluate_axiom(ollama, statement, justification)
                approved = evaluation["approved"]
                eval_reason = evaluation["reason"]
                evaluation_warning = bool(evaluation.get("evaluation_warning", False))

                axiom_id = str(uuid.uuid4())
                label = body.label or statement[:60]
                if body.label and len(proposals) > 1:
                    label = f"{body.label} #{idx}"

                await session.run(
                    cypher,
                    id=axiom_id,
                    label=label,
                    statement=statement,
                    justification=justification,
                    confidence=confidence,
                    approved=approved,
                    eval_reason=eval_reason,
                    evaluation_warning=evaluation_warning,
                    created_at=created_at,
                )

                responses.append(
                    AxiomResponse(
                        axiom_id=axiom_id,
                        label=label,
                        statement=statement,
                        justification=justification,
                        confidence=confidence,
                        approved=approved,
                        eval_reason=eval_reason,
                        evaluation_warning=evaluation_warning,
                        created_at=created_at,
                        persisted=True,
                    )
                )
    finally:
        if should_close:
            await driver.close()

    return responses


@router.get("/axioms")
async def list_axioms(
    limit: int = Query(default=50, ge=1, le=500),
) -> list[dict]:
    """List axioms stored in Neo4j, newest first."""
    if not settings.axiom_axiomatizer_enabled:
        raise HTTPException(status_code=503, detail="Axiomatizer is disabled.")

    driver, should_close = await _get_driver(None)
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
        if should_close:
            await driver.close()
    return rows
