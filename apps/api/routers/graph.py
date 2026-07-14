"""Graph data endpoints — nodes and edges for the UI graph view."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from neo4j import AsyncDriver
from pydantic import BaseModel

from apps.api.dependencies import get_driver

router = APIRouter(prefix="/graph", tags=["graph"])


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    properties: dict


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str


class GraphNodesResponse(BaseModel):
    nodes: list[GraphNode]


class GraphEdgesResponse(BaseModel):
    edges: list[GraphEdge]


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    links: list[GraphEdge]


NODES_CYPHER = """
MATCH (n)
WHERE n:Query OR n:Finding OR n:Source OR n:Axiom
RETURN
    coalesce(n.id, n.url, n.label, n.text, n.title) AS id,
    coalesce(n.label, n.statement, n.text, n.title, n.url, labels(n)[0]) AS label,
    labels(n)[0] AS type,
    properties(n) AS props
LIMIT 500
"""

EDGES_CYPHER = """
MATCH (a)-[r]->(b)
WHERE (a:Query OR a:Finding OR a:Source OR a:Axiom)
  AND (b:Query OR b:Finding OR b:Source OR b:Axiom)
RETURN
    toString(id(a)) AS source,
    toString(id(b)) AS target,
    type(r) AS type
LIMIT 2000
"""


async def _load_nodes(driver: AsyncDriver) -> list[GraphNode]:
    nodes: list[GraphNode] = []
    async with driver.session() as session:
        result = await session.run(NODES_CYPHER)
        async for record in result:
            nodes.append(
                GraphNode(
                    id=record["id"],
                    label=str(record["label"]),
                    type=record["type"],
                    properties=dict(record["props"]),
                )
            )
    return nodes


async def _load_edges(driver: AsyncDriver) -> list[GraphEdge]:
    edges: list[GraphEdge] = []
    async with driver.session() as session:
        result = await session.run(EDGES_CYPHER)
        async for record in result:
            edges.append(
                GraphEdge(
                    source=record["source"],
                    target=record["target"],
                    type=record["type"],
                )
            )
    return edges


@router.get("", response_model=GraphResponse)
async def get_graph(driver: AsyncDriver = Depends(get_driver)):
    """Return combined graph payload for the web UI: {nodes, links}."""
    nodes = await _load_nodes(driver)
    edges = await _load_edges(driver)
    return GraphResponse(nodes=nodes, links=edges)


@router.get("/nodes", response_model=GraphNodesResponse)
async def get_nodes(driver: AsyncDriver = Depends(get_driver)):
    """Return all Query, Finding, Source, and Axiom nodes."""
    return GraphNodesResponse(nodes=await _load_nodes(driver))


@router.get("/edges", response_model=GraphEdgesResponse)
async def get_edges(driver: AsyncDriver = Depends(get_driver)):
    """Return all relationships between graph nodes."""
    return GraphEdgesResponse(edges=await _load_edges(driver))
