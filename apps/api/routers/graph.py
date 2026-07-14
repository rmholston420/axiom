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


@router.get("/nodes", response_model=GraphNodesResponse)
async def get_nodes(driver: AsyncDriver = Depends(get_driver)):
    """Return all Query, Finding, and Source nodes."""
    cypher = """
    MATCH (n)
    WHERE n:Query OR n:Finding OR n:Source
    RETURN
        toString(id(n))        AS id,
        labels(n)[0]           AS label,
        labels(n)[0]           AS type,
        properties(n)          AS props
    LIMIT 500
    """
    nodes: list[GraphNode] = []
    async with driver.session() as session:
        result = await session.run(cypher)
        async for record in result:
            nodes.append(
                GraphNode(
                    id=record["id"],
                    label=record["label"],
                    type=record["type"],
                    properties=dict(record["props"]),
                )
            )
    return GraphNodesResponse(nodes=nodes)


@router.get("/edges", response_model=GraphEdgesResponse)
async def get_edges(driver: AsyncDriver = Depends(get_driver)):
    """Return all relationships between Query/Finding/Source nodes."""
    cypher = """
    MATCH (a)-[r]->(b)
    WHERE (a:Query OR a:Finding OR a:Source)
      AND (b:Query OR b:Finding OR b:Source)
    RETURN
        toString(id(a)) AS source,
        toString(id(b)) AS target,
        type(r)         AS type
    LIMIT 2000
    """
    edges: list[GraphEdge] = []
    async with driver.session() as session:
        result = await session.run(cypher)
        async for record in result:
            edges.append(
                GraphEdge(
                    source=record["source"],
                    target=record["target"],
                    type=record["type"],
                )
            )
    return GraphEdgesResponse(edges=edges)
