"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import Shell from "@/components/Shell";
import { fetchGraph, type GraphData } from "@/lib/api";
import { RefreshCw, Loader2, Box, Orbit } from "lucide-react";

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

export default function GraphPage() {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [mode, setMode] = useState<GraphMode>("2d");
  const [hoverNodeId, setHoverNodeId] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const fg2dRef = useRef<any>(null);
  const fg3dRef = useRef<any>(null);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const d = await fetchGraph();
      setData(d);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const nodeColorMap: Record<string, string> = {
    Query: "#4f98a3",
    Finding: "#6daa45",
    Source: "#da7101",
  };

  const graphData = useMemo(() => {
    if (!data) return null;

    const nodes: GraphNode[] = data.nodes.map((node) => ({
      id: String(node.id),
      label: String(node.label),
      type: String(node.type),
    }));

    const links: GraphLink[] = data.links.map((link, index) => ({
      id: `${String(link.source)}-${String(link.target)}-${String(link.type)}-${index}`,
      source: String(link.source),
      target: String(link.target),
      type: String(link.type),
    }));

    return { nodes, links };
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
      fg.d3Force("link")?.distance?.((link: any) => {
        const sourceId = typeof link.source === "string" ? link.source : link.source.id;
        const targetId = typeof link.target === "string" ? link.target : link.target.id;
        const activeId = hoverNodeId ?? selectedNodeId;
        if (!activeId) return 140;
        return sourceId === activeId || targetId === activeId ? 190 : 150;
      });

      fg.d3ReheatSimulation();
      setTimeout(() => {
        try {
          fg.zoomToFit(800, 80);
        } catch {}
      }, 250);
    } catch {}
  }, [graphData, hoverNodeId, selectedNodeId]);


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
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "1rem",
          marginBottom: "1.5rem",
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--color-text)" }}>
            Graph
          </h1>

          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.5rem",
              padding: "0.25rem",
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-lg)",
            }}
          >
            <button
              type="button"
              onClick={() => setMode("2d")}
              style={toggleButtonStyle(mode === "2d")}
            >
              <Box size={14} />
              2D
            </button>
            <button
              type="button"
              onClick={() => setMode("3d")}
              style={toggleButtonStyle(mode === "3d")}
            >
              <Orbit size={14} />
              3D
            </button>
          </div>

          <button
            onClick={load}
            disabled={loading}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.375rem",
              padding: "0.4rem 0.875rem",
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
              color: "var(--color-text-muted)",
              fontSize: "0.8125rem",
              cursor: loading ? "not-allowed" : "pointer",
            }}
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

      <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        {[
          ["Query", "#4f98a3"],
          ["Finding", "#6daa45"],
          ["Source", "#da7101"],
        ].map(([label, color]) => (
          <div
            key={label}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.375rem",
              fontSize: "0.8125rem",
              color: "var(--color-text-muted)",
            }}
          >
            <span
              style={{
                width: "10px",
                height: "10px",
                borderRadius: "50%",
                background: color,
                display: "inline-block",
              }}
            />
            {label}
          </div>
        ))}
      </div>

      {error && (
        <div style={{ color: "#d163a7", fontSize: "0.875rem", marginBottom: "1rem" }}>
          Could not load graph: {error}
        </div>
      )}

      <div
        style={{
          width: "100%",
          height: "calc(100dvh - 220px)",
          background: mode === "3d" ? "#09090b" : "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-lg)",
          overflow: "hidden",
        }}
      >
        {graphData && mode === "2d" && (
        <ForceGraph2D
          ref={fg2dRef}
          graphData={graphData}
          nodeId="id"
          linkSource="source"
          linkTarget="target"
          backgroundColor="#0d0d0f"
          onNodeHover={(node: any) => setHoverNodeId(node?.id ?? null)}
          onNodeClick={(node: any) => setSelectedNodeId(node?.id ?? null)}
          onBackgroundClick={() => setSelectedNodeId(null)}
          onBackgroundClick={() => setSelectedNodeId(null)}
          nodeLabel={(node: any) => `${node.type}: ${node.label}`}
          nodeRelSize={6}
          linkWidth={(link: any) => {
            const sourceId = typeof link.source === "string" ? link.source : link.source.id;
            const targetId = typeof link.target === "string" ? link.target : link.target.id;
            const activeId = hoverNodeId ?? selectedNodeId;
            if (!activeId) return 1.8;
            return sourceId === activeId || targetId === activeId ? 6 : 0.45;
          }}
          linkColor={(link: any) => {
            const sourceId = typeof link.source === "string" ? link.source : link.source.id;
            const targetId = typeof link.target === "string" ? link.target : link.target.id;
            const activeId = hoverNodeId ?? selectedNodeId;
            if (!activeId) return "rgba(110,140,170,0.42)";
            return sourceId === activeId || targetId === activeId
              ? "rgba(255,196,87,1)"
              : "rgba(90,90,96,0.08)";
          }}
          linkDirectionalParticles={(link: any) => {
            const sourceId = typeof link.source === "string" ? link.source : link.source.id;
            const targetId = typeof link.target === "string" ? link.target : link.target.id;
            const activeId = hoverNodeId ?? selectedNodeId;
            if (!activeId) return 0;
            return sourceId === activeId || targetId === activeId ? 4 : 0;
          }}
          linkDirectionalParticleWidth={4}
          linkDirectionalParticleColor={() => "#ffc457"}
          nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
            const hasFocus = Boolean(hoverNodeId ?? selectedNodeId);
            const isActive = (hoverNodeId ?? selectedNodeId) === node.id;
            const isNeighbor = hasFocus ? neighborIds.has(node.id) : true;
            const label = String(node.label ?? "");
            const color = nodeColorMap[node.type] ?? "#4f98a3";
            const radius = hasFocus ? (isActive ? 8 : isNeighbor ? 5.75 : 4.1) : (isActive ? 7 : 5.5);

            ctx.beginPath();
            ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
            ctx.fillStyle = isNeighbor ? color : "rgba(100,100,100,0.35)";
            ctx.fill();
            ctx.lineWidth = isActive ? 2 : 1;
            ctx.strokeStyle = isActive ? "#fdab43" : "rgba(255,255,255,0.28)";
            ctx.stroke();

            const shouldDrawLabel = hasFocus ? isNeighbor : globalScale >= 1.1 || isActive;

            if (shouldDrawLabel) {
              const fontSize = Math.max(10, 14 / globalScale);
              ctx.font = `${fontSize}px Inter, sans-serif`;
              ctx.textAlign = "left";
              ctx.textBaseline = "middle";
              const textWidth = ctx.measureText(label).width;
              const padX = 6 / globalScale;
              const padY = 3 / globalScale;
              const x = node.x + 10;
              const y = node.y;

              ctx.fillStyle = "rgba(13,13,15,0.9)";
              ctx.fillRect(x - padX, y - fontSize / 2 - padY, textWidth + padX * 2, fontSize + padY * 2);

              ctx.fillStyle = "#f5f5f5";
              ctx.fillText(label, x, y);
            }
          }}
        />
      )}

        {graphData && mode === "3d" && (
        <ForceGraph3D
          ref={fg3dRef}
          graphData={graphData}
          nodeId="id"
          linkSource="source"
          linkTarget="target"
          backgroundColor="#09090b"
          onNodeHover={(node: any) => setHoverNodeId(node?.id ?? null)}
          onNodeClick={(node: any) => setSelectedNodeId(node?.id ?? null)}
          onBackgroundClick={() => setSelectedNodeId(null)}
          nodeLabel={(node: any) => `${node.type}: ${node.label}`}
          nodeAutoColorBy="type"
          nodeVal={(node: any) => {
            const activeId = hoverNodeId ?? selectedNodeId;
            if (!activeId) return 5;
            return neighborIds.has(node.id) ? (node.id === activeId ? 7 : 5) : 2.2;
          }}
          nodeOpacity={0.95}
          linkColor={(link: any) => {
            const sourceId = typeof link.source === "string" ? link.source : link.source.id;
            const targetId = typeof link.target === "string" ? link.target : link.target.id;
            const activeId = hoverNodeId ?? selectedNodeId;
            if (!activeId) return "rgba(170,210,255,0.9)";
            return sourceId === activeId || targetId === activeId
              ? "rgba(255,215,120,1)"
              : "rgba(120,120,130,0.2)";
          }}
          linkCurvature={(link: any) => {
            const sourceId = typeof link.source === "string" ? link.source : link.source.id;
            const targetId = typeof link.target === "string" ? link.target : link.target.id;
            const seed = Array.from(`${sourceId}-${targetId}`).reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
            const base = ((seed % 5) - 2) * 0.12;
            const activeId = hoverNodeId ?? selectedNodeId;
            if (!activeId) return base;
            return sourceId === activeId || targetId === activeId ? base * 1.4 : base;
          }}
          linkCurveRotation={(link: any) => {
            const sourceId = typeof link.source === "string" ? link.source : link.source.id;
            const targetId = typeof link.target === "string" ? link.target : link.target.id;
            const seed = Array.from(`${targetId}-${sourceId}`).reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
            return (seed % 12) * (Math.PI / 6);
          }}
          linkDirectionalParticles={(link: any) => {
            const sourceId = typeof link.source === "string" ? link.source : link.source.id;
            const targetId = typeof link.target === "string" ? link.target : link.target.id;
            const activeId = hoverNodeId ?? selectedNodeId;
            if (!activeId) return 1;
            return sourceId === activeId || targetId === activeId ? 5 : 0;
          }}
          linkDirectionalParticleWidth={4}
          linkDirectionalParticleColor={() => "#ffd778"}
          linkDirectionalArrowLength={10}
          linkDirectionalArrowRelPos={1}
          linkOpacity={1}
        />
      )}

        {loading && !graphData && (
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              height: "100%",
              color: "var(--color-text-muted)",
            }}
          >
            <Loader2 size={24} className="animate-spin" />
          </div>
        )}
      </div>
    </Shell>
  );
}
