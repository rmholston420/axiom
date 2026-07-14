"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
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
  source: string;
  target: string;
  type: string;
};

export default function GraphPage() {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [mode, setMode] = useState<GraphMode>("2d");

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
          {mode === "2d" ? "Drag to pan, scroll to zoom." : "Drag to orbit, scroll to zoom."}
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
            graphData={graphData}
            nodeId="id"
            linkSource="source"
            linkTarget="target"
            backgroundColor="#0d0d0f"
            nodeLabel="label"
            nodeColor={(node) =>
              nodeColorMap[String((node as { type?: unknown })?.type ?? "")] ?? "#7a7a82"
            }
            linkColor={() => "#2a2a2e"}
            nodeRelSize={6}
            linkDirectionalArrowLength={4}
            linkDirectionalArrowRelPos={1}
          />
        )}

        {graphData && mode === "3d" && (
          <ForceGraph3D
            graphData={graphData}
            nodeId="id"
            linkSource="source"
            linkTarget="target"
            backgroundColor="#09090b"
            nodeLabel="label"
            nodeColor={(node) =>
              nodeColorMap[String((node as { type?: unknown })?.type ?? "")] ?? "#7a7a82"
            }
            linkColor={() => "#3a3a40"}
            linkOpacity={0.45}
            nodeRelSize={5}
            linkDirectionalArrowLength={3.5}
            linkDirectionalArrowRelPos={1}
            enableNodeDrag
            showNavInfo={false}
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
