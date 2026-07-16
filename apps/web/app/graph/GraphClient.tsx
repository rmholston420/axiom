"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import Shell from "@/components/Shell";
import { fetchAxioms, fetchGraph, type AxiomRecord, type GraphData } from "@/lib/api";
import { RefreshCw, Loader2, Box, Orbit } from "lucide-react";
import type { ForceGraphMethods } from "react-force-graph-2d";

const ForceGraph2D = dynamic(
  () => import("react-force-graph-2d").then((mod) => mod.default),
  { ssr: false }
);

const ForceGraph3D = dynamic(
  () => import("react-force-graph-3d").then((mod) => mod.default),
  { ssr: false }
);

type GraphMode = "2d" | "3d";

type GraphNode = {
  id: string;
  label: string;
  type: string;
};

type GraphLink = {
  id: string;
  source: string | GraphNode;
  target: string | GraphNode;
  type: string;
};


type GraphNodeDatum = {
  id?: string | number;
  label?: string;
  type?: string;
  x?: number;
  y?: number;
};

type GraphLinkDatum = {
  source: string | GraphNodeDatum;
  target: string | GraphNodeDatum;
  type?: string;
};


type ForceLinkObject = {
  source?: string | number | GraphNodeDatum;
  target?: string | number | GraphNodeDatum;
  relationship?: string;
  weight?: number;
};

type ForceGraphInstance = {
  d3Force: (name: string) => {
    distance?: (fn: (link: GraphLinkDatum) => number) => void;
  } | undefined;
  d3ReheatSimulation: () => void;
  zoomToFit: (durationMs?: number, paddingPx?: number) => void;
};


function getNodeId(node: string | GraphNodeDatum | null | undefined): string {
  if (typeof node === "string") return node;
  return String(node?.id ?? "");
}

function getNodeLabel(node: GraphNodeDatum | null | undefined): string {
  return String(node?.label ?? node?.id ?? "node");
}

function getNodeType(node: GraphNodeDatum | null | undefined): string {
  return String(node?.type ?? "Unknown");
}

export default function GraphClient({
  initialGraph,
  initialAxioms,
}: {
  initialGraph: GraphData;
  initialAxioms: AxiomRecord[];
}) {
  const [data, setData] = useState<GraphData | null>(initialGraph);
  const [axioms, setAxioms] = useState<AxiomRecord[]>(initialAxioms);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState<GraphMode>("2d");
  const [hoverNodeId, setHoverNodeId] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const fg2dRef = useRef<ForceGraphMethods<GraphNodeDatum, GraphLinkDatum> | undefined>(undefined);
  const fg3dRef = useRef<any>(undefined);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [d, a] = await Promise.all([fetchGraph(), fetchAxioms(25)]);
      setData(d);
      setAxioms(a);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const nodeColorMap: Record<string, string> = {
    Query: "#4f98a3",
    Finding: "#6daa45",
    Source: "#da7101",
    Axiom: "#d163a7",
  };

  const graphData = useMemo(() => {
    if (!data) return null;

    const nodes: GraphNode[] = data.nodes.map((node) => ({
      id: String(node.id),
      label: String(node.label),
      type: String(node.type),
    }));

    const nodeIds = new Set(nodes.map((node) => node.id));

    const links: GraphLink[] = data.links
      .map((link, index) => ({
        id: `${String(link.source)}-${String(link.target)}-${String(link.type)}-${index}`,
        source: String(link.source),
        target: String(link.target),
        type: String(link.type),
      }))
      .filter((link) => nodeIds.has(String(link.source)) && nodeIds.has(String(link.target)));

    return { nodes, links };
  }, [data]);

  useEffect(() => {
    if (!data) return;
    const nodeIds = new Set(data.nodes.map((node) => String(node.id)));
    const missing = data.links.filter(
      (link) => !nodeIds.has(String(link.source)) || !nodeIds.has(String(link.target)),
    );
    if (missing.length > 0) {
    }
  }, [data]);

  const neighborIds = useMemo(() => {
    const activeId = hoverNodeId ?? selectedNodeId;
    const set = new Set<string>();
    if (!graphData || !activeId) return set;

    set.add(activeId);
    for (const link of graphData.links) {
      const sourceId = typeof link.source === "string" ? link.source : link.source.id;
      const targetId = typeof link.target === "string" ? link.target : link.target.id;
      if (sourceId === activeId) set.add(targetId);
      if (targetId === activeId) set.add(sourceId);
    }
    return set;
  }, [graphData, hoverNodeId, selectedNodeId]);

  const selectedNode = useMemo(() => {
    if (!graphData || !selectedNodeId) return null;
    return graphData.nodes.find((node) => node.id === selectedNodeId) ?? null;
  }, [graphData, selectedNodeId]);

  const selectedLinks = useMemo(() => {
    if (!graphData || !selectedNodeId) return [];
    return graphData.links.filter((link) => {
      const sourceId = typeof link.source === "string" ? link.source : link.source.id;
      const targetId = typeof link.target === "string" ? link.target : link.target.id;
      return sourceId === selectedNodeId || targetId === selectedNodeId;
    });
  }, [graphData, selectedNodeId]);

  useEffect(() => {
    if (!graphData || !fg3dRef.current) return;
    const fg = fg3dRef.current;
    try {
      fg.d3Force("link")?.distance?.((link: GraphLinkDatum) => {
        const sourceId = typeof link.source === "string" ? link.source : link.source.id;
        const targetId = typeof link.target === "string" ? link.target : link.target.id;
        return sourceId === targetId ? 120 : 145;
      });
      fg.d3ReheatSimulation();
      window.setTimeout(() => {
        try {
          fg.zoomToFit(800, 80);
        } catch {}
      }, 250);
    } catch {}
  }, [graphData]);

  const toggleButtonStyle = (active: boolean): React.CSSProperties => ({
    display: "inline-flex",
    alignItems: "center",
    gap: "0.375rem",
    padding: "0.45rem 0.85rem",
    background: active ? "oklch(from var(--color-primary) l c h / 0.14)" : "var(--color-surface)",
    border: `1px solid ${active ? "var(--color-primary)" : "var(--color-border)"}`,
    borderRadius: "var(--radius-md)",
    color: active ? "var(--color-primary)" : "var(--color-text-muted)",
    fontSize: "0.8125rem",
    fontWeight: active ? 600 : 500,
    cursor: "pointer",
  });

  return (
    <Shell>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--color-text)" }}>Graph</h1>
          <div style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem", padding: "0.25rem", background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-lg)" }}>
            <button type="button" onClick={() => setMode("2d")} style={toggleButtonStyle(mode === "2d")}><Box size={14} />2D</button>
            <button type="button" onClick={() => setMode("3d")} style={toggleButtonStyle(mode === "3d")}><Orbit size={14} />3D</button>
          </div>
          <button
            onClick={load}
            disabled={loading}
            style={{ display: "flex", alignItems: "center", gap: "0.375rem", padding: "0.4rem 0.875rem", background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", color: "var(--color-text-muted)", fontSize: "0.8125rem", cursor: loading ? "not-allowed" : "pointer" }}
          >
            {loading ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
            Refresh
          </button>
        </div>
        <div style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
          {mode === "2d"
            ? "Drag to pan, scroll to zoom, hover nodes to highlight connected links, click to pin details."
            : "Drag to orbit, scroll to zoom, hover nodes to highlight connected links, click to pin details."}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "0.75rem", marginBottom: "1rem" }}>
        <div style={{ padding: "0.9rem 1rem", background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-lg)" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Nodes</div>
          <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--color-text)", marginTop: "0.25rem" }}>{graphData?.nodes.length ?? 0}</div>
        </div>
        <div style={{ padding: "0.9rem 1rem", background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-lg)" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Links</div>
          <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--color-text)", marginTop: "0.25rem" }}>{graphData?.links.length ?? 0}</div>
        </div>
        <div style={{ padding: "0.9rem 1rem", background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-lg)" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Axioms</div>
          <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--color-text)", marginTop: "0.25rem" }}>{axioms.length}</div>
        </div>
      </div>

      <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        {[
          ["Query", "#4f98a3"],
          ["Finding", "#6daa45"],
          ["Source", "#da7101"],
          ["Axiom", "#d163a7"],
        ].map(([label, color]) => (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: "0.375rem", fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
            <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: color, display: "inline-block" }} />
            {label}
          </div>
        ))}
      </div>

      {error && (
        <div style={{ marginBottom: "1rem", padding: "0.875rem 1rem", borderRadius: "var(--radius-md)", border: "1px solid var(--color-error)", color: "var(--color-error)", background: "oklch(from var(--color-error) l c h / 0.08)" }}>
          {error}
        </div>
      )}

      <div style={{ width: "100%", height: "calc(100dvh - 220px)", background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-lg)", overflow: "hidden" }}>
        {!graphData ? (
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100%", color: "var(--color-text-muted)" }}>
            <Loader2 className="animate-spin" />
          </div>
        ) : mode === "2d" ? (
          <ForceGraph2D
            ref={fg2dRef}
            graphData={graphData}
            nodeLabel={(node: GraphNodeDatum) => `${getNodeLabel(node)} (${getNodeType(node)})`}
            linkLabel={(link: ForceLinkObject) => getLinkRelationship(link)}
            nodeRelSize={7}
                        onNodeHover={(node: GraphNodeDatum | null) => setHoverNodeId(node?.id != null ? String(node.id) : null)}
            onNodeClick={(node: GraphNodeDatum) => setSelectedNodeId(node?.id != null ? String(node.id) : null)}
            nodeCanvasObject={(node: GraphNodeDatum, ctx: CanvasRenderingContext2D, globalScale: number) => {
              const nodeId = String(node.id ?? "");
            const isActive = neighborIds.size === 0 || neighborIds.has(nodeId);
            const color = nodeColorMap[String(node.type ?? "")] ?? "#888";
            const isFocused = hoverNodeId === nodeId || selectedNodeId === nodeId;
            if (node.x == null || node.y == null) return;
            const fontSize = Math.max(10, 12 / globalScale);
            const radius = isFocused ? (isActive ? 9 : 7.5) : (isActive ? 7 : 5.5);
            ctx.beginPath();
            ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
              ctx.fillStyle = isActive ? color : "rgba(148, 163, 184, 0.35)";
              ctx.fill();
              ctx.font = `${fontSize}px sans-serif`;
              ctx.fillStyle = isActive ? "#e5e7eb" : "rgba(148, 163, 184, 0.6)";
              ctx.fillText(String(node.label ?? node.id ?? "node"), (node.x ?? 0) + 10, (node.y ?? 0) + 4);
            }}
          linkColor={(link: ForceLinkObject) => {
            const relationship = getLinkRelationship(link);
            const sourceId = getLinkEndpointId(link.source);
            const targetId = getLinkEndpointId(link.target);
            const denseNeighborhood = neighborIds.has(sourceId) && neighborIds.has(targetId);

            const isFocused =
              (hoverNodeId != null && (sourceId === hoverNodeId || targetId === hoverNodeId)) ||
              (selectedNodeId != null && (sourceId === selectedNodeId || targetId === selectedNodeId));

            const strongAlphaBase = denseNeighborhood ? 0.95 : 0.8;
            const softAlphaBase = denseNeighborhood ? 0.55 : 0.35;

            const strongAlpha = isFocused ? strongAlphaBase : strongAlphaBase * 0.7;
            const softAlpha = isFocused ? softAlphaBase : softAlphaBase * 0.6;

            if (relationship === "MENTIONS" || relationship === "SUPPORTS") {
              return `rgba(79,163,163,${strongAlpha})`;
            }
            if (relationship === "CONTRADICTS") {
              return `rgba(245,158,11,${strongAlpha})`;
            }
            return `rgba(148,163,184,${softAlpha})`;
          }}
          linkWidth={(link: ForceLinkObject) => {
            const sourceId = getLinkEndpointId(link.source);
            const targetId = getLinkEndpointId(link.target);
            const denseNeighborhood = neighborIds.has(sourceId) && neighborIds.has(targetId);

            const isFocused =
              (hoverNodeId != null && (sourceId === hoverNodeId || targetId === hoverNodeId)) ||
              (selectedNodeId != null && (sourceId === selectedNodeId || targetId === selectedNodeId));

            if (isFocused && denseNeighborhood) return 3.2;
            if (isFocused) return 2.4;
            return denseNeighborhood ? 1.8 : 1;
          }}
          />
        ) : (
          <ForceGraph3D
           ref={fg3dRef}
           graphData={graphData}
           nodeVal={(node: GraphNodeDatum) => {
             const id = String(node.id);
             const isFocused = hoverNodeId === id || selectedNodeId === id;
             const inDenseNeighborhood = neighborIds.has(id);

             if (isFocused && inDenseNeighborhood) return 9;
             if (isFocused) return 7.2;
             return inDenseNeighborhood ? 5.8 : 4.6;
           }}
            linkCurvature={(link: ForceLinkObject) => {
            const sourceId = getLinkEndpointId(link.source);
            const targetId = getLinkEndpointId(link.target);
            const relationship = getLinkRelationship(link);

            const pair = [sourceId, targetId].sort().join("|");
            let hash = 0;
            for (let i = 0; i < pair.length; i += 1) {
              hash = (hash * 31 + pair.charCodeAt(i)) >>> 0;
            }

            const denseNeighborhood = neighborIds.has(sourceId) && neighborIds.has(targetId);

            const baseRelationship = relationship === "CONTRADICTS"
              ? 0.42
              : relationship === "MENTIONS" || relationship === "SUPPORTS"
                ? 0.3
                : 0.2;

            const baseDensity = denseNeighborhood ? 0.16 : 0.0;
            const base = baseRelationship + baseDensity;

            const offset = ((hash % 5) - 2) * 0.05;
            return Math.max(0.08, base + offset);
          }}
            linkCurveRotation={(link: ForceLinkObject) => {
            const sourceId = getLinkEndpointId(link.source);
            const targetId = getLinkEndpointId(link.target);
            const pair = [sourceId, targetId].sort().join("|");

            let hash = 0;
            for (let i = 0; i < pair.length; i += 1) {
              hash = (hash * 31 + pair.charCodeAt(i)) >>> 0;
            }

            const t = (hash % 1000) / 1000; // [0, 1)
            const angle = (t * 1.3) - 0.65; // roughly [-0.65, 0.65]
            return angle;
          }}
            nodeLabel={(node: GraphNodeDatum) => `${getNodeLabel(node)} (${getNodeType(node)})`}
            linkLabel={(link: ForceLinkObject) => getLinkRelationship(link)}
            nodeAutoColorBy="type"
                        onNodeHover={(node: GraphNodeDatum | null) => setHoverNodeId(node?.id != null ? String(node.id) : null)}
            onNodeClick={(node: GraphNodeDatum) => setSelectedNodeId(node?.id != null ? String(node.id) : null)}
            linkColor={(link: ForceLinkObject) => {
              const relationship = getLinkRelationship(link);
              if (relationship === "MENTIONS" || relationship === "SUPPORTS") return "rgba(79,163,163,0.8)";
              if (relationship === "CONTRADICTS") return "rgba(245,158,11,0.8)";
              return "rgba(148,163,184,0.35)";
            }}
          />
        )}
      </div>

      <div style={{ marginTop: "1rem", display: "grid", gap: "1rem", gridTemplateColumns: "minmax(0, 1.3fr) minmax(320px, 0.9fr)" }}>
        <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-lg)", overflow: "hidden" }}>
          <div style={{ padding: "1rem 1rem 0.5rem", borderBottom: "1px solid var(--color-border)" }}>
            <h2 style={{ margin: 0, fontSize: "1.1rem", color: "var(--color-text)" }}>Recent axioms</h2>
            <p style={{ margin: "0.35rem 0 0", fontSize: "0.875rem", color: "var(--color-text-muted)" }}>
              Latest persisted axioms from the axiomatizer service.
            </p>
          </div>

          {axioms.length === 0 ? (
            <div style={{ padding: "1rem", color: "var(--color-text-muted)" }}>No axioms have been persisted yet.</div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ background: "var(--color-surface-2)" }}>
                    <th style={{ textAlign: "left", padding: "0.75rem 1rem", fontSize: "0.8rem", color: "var(--color-text-muted)", borderBottom: "1px solid var(--color-border)" }}>Label</th>
                    <th style={{ textAlign: "left", padding: "0.75rem 1rem", fontSize: "0.8rem", color: "var(--color-text-muted)", borderBottom: "1px solid var(--color-border)" }}>Approved</th>
                    <th style={{ textAlign: "left", padding: "0.75rem 1rem", fontSize: "0.8rem", color: "var(--color-text-muted)", borderBottom: "1px solid var(--color-border)" }}>Confidence</th>
                    <th style={{ textAlign: "left", padding: "0.75rem 1rem", fontSize: "0.8rem", color: "var(--color-text-muted)", borderBottom: "1px solid var(--color-border)" }}>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {axioms.map((axiom) => (
                    <tr key={axiom.id}>
                      <td style={{ padding: "0.875rem 1rem", borderBottom: "1px solid var(--color-border)", color: "var(--color-text)" }}>
                        <div style={{ fontWeight: 600 }}>{axiom.label}</div>
                        <div style={{ marginTop: "0.3rem", fontSize: "0.85rem", color: "var(--color-text-muted)", maxWidth: "68ch" }}>
                          {axiom.statement}
                        </div>
                      </td>
                      <td style={{ padding: "0.875rem 1rem", borderBottom: "1px solid var(--color-border)" }}>
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            padding: "0.25rem 0.55rem",
                            borderRadius: "9999px",
                            fontSize: "0.78rem",
                            fontWeight: 600,
                            color: axiom.approved ? "#14532d" : "#7f1d1d",
                            background: axiom.approved ? "rgba(34,197,94,0.14)" : "rgba(239,68,68,0.14)",
                            border: axiom.approved ? "1px solid rgba(34,197,94,0.28)" : "1px solid rgba(239,68,68,0.28)",
                          }}
                        >
                          {axiom.approved ? "Approved" : "Rejected"}
                        </span>
                      </td>
                      <td style={{ padding: "0.875rem 1rem", borderBottom: "1px solid var(--color-border)", color: "var(--color-text)" }}>
                        {typeof axiom.confidence === "number" ? axiom.confidence.toFixed(2) : String(axiom.confidence)}
                      </td>
                      <td style={{ padding: "0.875rem 1rem", borderBottom: "1px solid var(--color-border)", color: "var(--color-text-muted)", whiteSpace: "nowrap" }}>
                        {new Date(axiom.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-lg)", overflow: "hidden" }}>
          <div style={{ padding: "1rem 1rem 0.5rem", borderBottom: "1px solid var(--color-border)" }}>
            <h2 style={{ margin: 0, fontSize: "1.1rem", color: "var(--color-text)" }}>Selection</h2>
            <p style={{ margin: "0.35rem 0 0", fontSize: "0.875rem", color: "var(--color-text-muted)" }}>
              Click a graph node to inspect its immediate connections.
            </p>
          </div>

          {!selectedNode ? (
            <div style={{ padding: "1rem", color: "var(--color-text-muted)" }}>No node selected.</div>
          ) : (
            <div style={{ padding: "1rem" }}>
              <div style={{ fontSize: "1rem", fontWeight: 700, color: "var(--color-text)" }}>{selectedNode.label}</div>
              <div style={{ marginTop: "0.35rem", fontSize: "0.85rem", color: "var(--color-text-muted)" }}>Type: {selectedNode.type}</div>
              <div style={{ marginTop: "1rem", fontSize: "0.85rem", color: "var(--color-text-muted)" }}>Connected edges</div>
              <div style={{ marginTop: "0.5rem", display: "grid", gap: "0.5rem" }}>
                {selectedLinks.length === 0 ? (
                  <div style={{ color: "var(--color-text-muted)" }}>No direct connections.</div>
                ) : (
                  selectedLinks.map((link) => {
                    const sourceId = typeof link.source === "string" ? link.source : link.source.id;
                    const targetId = typeof link.target === "string" ? link.target : link.target.id;
                    const otherId = sourceId === selectedNode.id ? targetId : sourceId;
                    const otherNode = graphData?.nodes.find((node) => node.id === otherId);
                    return (
                      <div key={link.id} style={{ padding: "0.65rem 0.75rem", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", background: "var(--color-surface-2)" }}>
                        <div style={{ fontWeight: 600, color: "var(--color-text)" }}>{link.type}</div>
                        <div style={{ marginTop: "0.2rem", fontSize: "0.84rem", color: "var(--color-text-muted)" }}>
                          {otherNode ? `${otherNode.label} (${otherNode.type})` : otherId}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </Shell>
  );
}


function getLinkEndpointId(endpoint: string | number | GraphNodeDatum | undefined): string {
  if (typeof endpoint === "string" || typeof endpoint === "number") {
    return String(endpoint);
  }
  if (endpoint && typeof endpoint === "object" && "id" in endpoint && endpoint.id != null) {
    return String(endpoint.id);
  }
  return "unknown";
}

function getLinkRelationship(link: ForceLinkObject): string {
  return link.relationship ?? "related_to";
}
