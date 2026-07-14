"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { fetchGraph, type GraphData } from "@/lib/api";
import { RefreshCw, Loader2 } from "lucide-react";

const ForceGraph2D = dynamic(
  () => import("react-force-graph-2d").then((mod) => mod.default),
  { ssr: false }
);

export default function GraphPage() {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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
    void load();
  }, []);

  const nodeColorMap: Record<string, string> = {
    Query: "#4f98a3",
    Finding: "#6daa45",
    Source: "#da7101",
  };

  const graphData = data
    ? {
        nodes: data.nodes.map((node) => ({
          ...node,
          id: String(node.id),
          label: String(node.label),
          type: String(node.type),
        })),
        links: data.links.map((link, index) => ({
          ...link,
          id: `${String(link.source)}-${String(link.target)}-${String(link.type)}-${index}`,
          source: String(link.source),
          target: String(link.target),
          type: String(link.type),
        })),
      }
    : null;

  const linkColorMap: Record<string, string> = {
    HASFINDING: "rgba(79, 152, 163, 0.8)",
    CITES: "rgba(245, 158, 11, 0.95)",
  };

  return (
    <Shell>
      <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--color-text)" }}>Graph</h1>
        <button
          onClick={() => void load()}
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

      <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        {[
          ["Query", "#4f98a3"],
          ["Finding", "#6daa45"],
          ["Source", "#da7101"],
          ["HASFINDING edge", "rgba(79, 152, 163, 0.8)"],
          ["CITES edge", "rgba(245, 158, 11, 0.95)"],
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
                width: "12px",
                height: "12px",
                borderRadius: label.includes("edge") ? "2px" : "50%",
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
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-lg)",
          overflow: "hidden",
        }}
      >
        {data && (
          <ForceGraph2D
            graphData={data}
            nodeId="id"
            linkSource="source"
            linkTarget="target"
            backgroundColor="#0d0d0f"
            nodeLabel="label"
            nodeColor={(node: any) => nodeColorMap[node.type] ?? "#c4c4cc"}
            linkColor={(link: any) => linkColorMap[link.type] ?? "rgba(180,180,190,0.55)"}
            linkWidth={(link: any) => link.type === "CITES" ? 2.2 : 1.5}
            nodeRelSize={7}
            cooldownTicks={120}
            linkDirectionalArrowLength={6}
            linkDirectionalArrowRelPos={1}
            linkDirectionalParticles={(link: any) => link.type === "CITES" ? 1 : 0}
            linkDirectionalParticleWidth={2}
          />
        )}

        {loading && !data && (
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
