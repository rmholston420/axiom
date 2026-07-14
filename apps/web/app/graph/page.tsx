"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2, RefreshCw } from "lucide-react";
import Shell from "@/components/Shell";
import { fetchGraph, type GraphData } from "@/lib/api";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

type FGNode = {
  id: string;
  label: string;
  type: string;
};

type FGLink = {
  source: string;
  target: string;
  type: string;
};

export default function GraphPage() {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await fetchGraph();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const kick = window.setTimeout(() => {
      void load();
    }, 0);

    return () => {
      window.clearTimeout(kick);
    };
  }, [load]);

  const graphData = useMemo(() => {
    if (!data) return { nodes: [] as FGNode[], links: [] as FGLink[] };
    return {
      nodes: data.nodes.map((n) => ({
        id: n.id,
        label: n.label,
        type: n.type,
      })),
      links: data.links.map((l, idx) => ({
        ...l,
        key: `${l.source}-${l.target}-${l.type}-${idx}`,
      })),
    };
  }, [data]);

  const nodeColor = (node: { type?: string }) => {
    if (node.type === "Query") return "#4f98a3";
    if (node.type === "Finding") return "#6daa45";
    if (node.type === "Source") return "#da7101";
    return "#8a8a93";
  };

  return (
    <Shell>
      <div style={{ maxWidth: 1280, margin: "0 auto" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.9rem", marginBottom: "1rem" }}>
          <h1 style={{ fontSize: "1.6rem", fontWeight: 700 }}>Graph</h1>
          <button
            type="button"
            onClick={() => void load()}
            disabled={loading}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.4rem",
              padding: "0.55rem 0.9rem",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--color-border)",
              background: "var(--color-surface)",
              color: "var(--color-text-muted)",
            }}
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            Refresh
          </button>
        </div>

        <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem", color: "var(--color-text-muted)", fontSize: "0.82rem" }}>
          {[
            ["Query", "#4f98a3"],
            ["Finding", "#6daa45"],
            ["Source", "#da7101"],
          ].map(([label, color]) => (
            <div key={String(label)} style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
              <span style={{ width: 10, height: 10, borderRadius: "999px", background: String(color), display: "inline-block" }} />
              {label}
            </div>
          ))}
        </div>

        {error && (
          <div
            style={{
              marginBottom: "1rem",
              padding: "0.85rem 1rem",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--color-border)",
              background: "var(--color-surface)",
              color: "var(--color-error)",
            }}
          >
            Could not load graph: {error}
          </div>
        )}

        <div
          style={{
            height: "calc(100dvh - 220px)",
            minHeight: 520,
            borderRadius: "var(--radius-lg)",
            overflow: "hidden",
            border: "1px solid var(--color-border)",
            background: "var(--color-surface)",
          }}
        >
          {loading && !data ? (
            <div
              style={{
                height: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--color-text-muted)",
              }}
            >
              <Loader2 size={22} className="animate-spin" />
            </div>
          ) : (
            <ForceGraph2D
              graphData={graphData}
              backgroundColor="#141416"
              nodeId="id"
              linkSource="source"
              linkTarget="target"
              nodeLabel={(node) => {
                const n = node as FGNode;
                return `${n.label}\nSchema: ${n.type}`;
              }}
              nodeColor={(node) => nodeColor(node as FGNode)}
              linkColor={() => "#2a2a2e"}
              linkDirectionalArrowLength={4}
              linkDirectionalArrowRelPos={1}
              nodeRelSize={6}
              cooldownTicks={120}
              d3AlphaMin={0.02}
            />
          )}
        </div>
      </div>
    </Shell>
  );
}
