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


NODE_ID_EXPR = "coalesce(n.id, n.url, n.label, n.text, n.title)"
EDGE_SOURCE_ID_EXPR = "coalesce(a.id, a.url, a.label, a.text, a.title)"
EDGE_TARGET_ID_EXPR = "coalesce(b.id, b.url, b.label, b.text, b.title)"

NODES_CYPHER = f"""
MATCH (n)
WHERE n:Query OR n:Finding OR n:Source OR n:Axiom
RETURN
    {NODE_ID_EXPR} AS id,
    coalesce(n.label, n.statement, n.text, n.title, n.url, labels(n)[0]) AS label,
    labels(n)[0] AS type,
    properties(n) AS props
ORDER BY coalesce(n.created_at, "")
LIMIT 2000
"""

EDGES_CYPHER = f"""
MATCH (a)-[r]->(b)
WHERE (a:Query OR a:Finding OR a:Source OR a:Axiom)
  AND (b:Query OR b:Finding OR b:Source OR b:Axiom)
RETURN
    {EDGE_SOURCE_ID_EXPR} AS source,
    {EDGE_TARGET_ID_EXPR} AS target,
    type(r) AS type
LIMIT 4000
"""


async def _load_nodes(driver: AsyncDriver) -> list[GraphNode]:
    nodes: list[GraphNode] = []
    async with driver.session() as session:
        result = await session.run(NODES_CYPHER)
        async for record in result:
            node_id = record["id"]
            if node_id is None:
                continue
            nodes.append(
                GraphNode(
                    id=str(node_id),
                    label=str(record["label"]),
                    type=str(record["type"]),
                    properties=dict(record["props"]),
                )
            )
    return nodes


async def _load_edges(driver: AsyncDriver, allowed_node_ids: set[str] | None = None) -> list[GraphEdge]:
    edges: list[GraphEdge] = []
    async with driver.session() as session:
        result = await session.run(EDGES_CYPHER)
        async for record in result:
            source = record["source"]
            target = record["target"]
            if source is None or target is None:
                continue
            source = str(source)
            target = str(target)
            if allowed_node_ids is not None and (source not in allowed_node_ids or target not in allowed_node_ids):
                continue
            edges.append(
                GraphEdge(
                    source=source,
                    target=target,
                    type=str(record["type"]),
                )
            )
    return edges


@router.get("", response_model=GraphResponse)
async def get_graph(driver: AsyncDriver = Depends(get_driver)):
    """Return combined graph payload for the web UI: {nodes, links}."""
    nodes = await _load_nodes(driver)
    node_ids = {node.id for node in nodes}
    edges = await _load_edges(driver, allowed_node_ids=node_ids)
    return GraphResponse(nodes=nodes, links=edges)


@router.get("/nodes", response_model=GraphNodesResponse)
async def get_nodes(driver: AsyncDriver = Depends(get_driver)):
    """Return all Query, Finding, Source, and Axiom nodes."""
    return GraphNodesResponse(nodes=await _load_nodes(driver))


@router.get("/edges", response_model=GraphEdgesResponse)
async def get_edges(driver: AsyncDriver = Depends(get_driver)):
    """Return all relationships between graph nodes."""
    nodes = await _load_nodes(driver)
    node_ids = {node.id for node in nodes}
    return GraphEdgesResponse(edges=await _load_edges(driver, allowed_node_ids=node_ids))
