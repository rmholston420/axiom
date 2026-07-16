"""FastAPI router — /wiki endpoints.

Exposes:
  GET  /wiki/pages              list all wiki pages (stubs)
  GET  /wiki/pages/{page_id}    get full markdown for one page
  POST /wiki/generate/query/{query_id}    regenerate topic page
  POST /wiki/generate/axiom/{axiom_id}    regenerate axiom page
  POST /wiki/generate/source              regenerate source page (url in body)
  DELETE /wiki/pages/{page_id}            remove a page
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

router = APIRouter(prefix="/wiki", tags=["wiki"])


# ---------------------------------------------------------------------------
# Dependency helpers — these are resolved from the app's lifespan state.
# The generator instance is stored on app.state.wiki_generator by main.py.
# ---------------------------------------------------------------------------

def _get_generator(request: Any) -> Any:
    gen = getattr(request.app.state, "wiki_generator", None)
    if gen is None:
        raise HTTPException(status_code=503, detail="WikiGenerator not initialised")
    return gen


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class SourcePageRequest(BaseModel):
    url: str


class WikiPageStubResponse(BaseModel):
    page_id: str
    page_type: str
    title: str
    slug: str
    generated_at: str
    version: int


class WikiPageResponse(BaseModel):
    page_id: str
    page_type: str
    title: str
    slug: str
    markdown: str
    content_hash: str
    version: int
    generated_at: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/pages", response_model=list[WikiPageStubResponse])
async def list_pages(request: Request, limit: int = 100) -> list[WikiPageStubResponse]:
    """Return stubs for all wiki pages, newest first."""
    gen = _get_generator(request)
    rows = await gen.list_pages(limit=limit)
    return [WikiPageStubResponse(**r) for r in rows]


@router.get("/pages/{page_id:path}", response_model=WikiPageResponse)
async def get_page(page_id: str, request: Request) -> WikiPageResponse:
    """Return full page data including rendered markdown."""
    gen = _get_generator(request)
    data = await gen.get_page(page_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Wiki page not found")
    return WikiPageResponse(**data)


@router.post("/generate/query/{query_id}", response_model=WikiPageStubResponse)
async def generate_query_page(query_id: str, request: Request) -> WikiPageStubResponse:
    """Trigger regeneration of a topic page from a Query node."""
    gen = _get_generator(request)
    try:
        page = await gen.generate_query_page(query_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return WikiPageStubResponse(
        page_id=page.page_id,
        page_type=page.page_type.value,
        title=page.title,
        slug=page.slug,
        generated_at=page.generated_at,
        version=page.version,
    )


@router.post("/generate/axiom/{axiom_id}", response_model=WikiPageStubResponse)
async def generate_axiom_page(axiom_id: str, request: Request) -> WikiPageStubResponse:
    """Trigger regeneration of an Axiom page."""
    gen = _get_generator(request)
    try:
        page = await gen.generate_axiom_page(axiom_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return WikiPageStubResponse(
        page_id=page.page_id,
        page_type=page.page_type.value,
        title=page.title,
        slug=page.slug,
        generated_at=page.generated_at,
        version=page.version,
    )


@router.post("/generate/source", response_model=WikiPageStubResponse)
async def generate_source_page(body: SourcePageRequest, request: Request) -> WikiPageStubResponse:
    """Trigger regeneration of a Source page."""
    gen = _get_generator(request)
    try:
        page = await gen.generate_source_page(body.url)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return WikiPageStubResponse(
        page_id=page.page_id,
        page_type=page.page_type.value,
        title=page.title,
        slug=page.slug,
        generated_at=page.generated_at,
        version=page.version,
    )


@router.delete("/pages/{page_id:path}", status_code=204, response_class=Response)
async def delete_page(page_id: str, request: Request) -> Response:
    """Remove a wiki page from the graph."""
    gen = _get_generator(request)
    await gen.delete_page(page_id)
    return Response(status_code=204)
