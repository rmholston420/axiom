"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import Shell from "@/components/Shell";
import { fetchGraph, type GraphData } from "@/lib/api";
import { Loader2, RefreshCw, Network } from "lucide-react";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

type ForceNode = {
  id: string;
  label?: string;
  type?: string;
};

type ForceLink = {
  source: string;
  target: string;
  type?: string;
};

export default function GraphPage() {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const result = await fetchGraph();
      setData(result);
    } catch (err) {
      setData(null);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const graphData = useMemo(() => {
    return {
      nodes: (data?.nodes ?? []).map((n) => ({
        id: n.id,
        label: n.label ?? n.id,
        type: n.type ?? n.group ?? "Node",
      })) as ForceNode[],
      links: (data?.links ?? []).map((l) => ({
        source: l.source,
        target: l.target,
        type: l.type ?? l.label ?? "RELATES_TO",
      })) as ForceLink[],
    };
  }, [data]);

  const hasGraph = graphData.nodes.length > 0 || graphData.links.length > 0;

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

      <div style={{ marginBottom: "1rem", color: "var(--color-text-muted)", fontSize: "0.875rem" }}>
        Slice 4 expects graph data from the API, but your backend does not expose that endpoint yet.
      </div>

      {error && (
        <div
          style={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-lg)",
            padding: "1rem",
            marginBottom: "1rem",
            color: "#d163a7",
            fontSize: "0.875rem",
          }}
        >
          {error}
        </div>
      )}

      {!hasGraph && (
        <div
          style={{
            display: "grid",
            placeItems: "center",
            minHeight: "420px",
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-lg)",
            color: "var(--color-text-muted)",
            textAlign: "center",
            padding: "2rem",
          }}
        >
          <div>
            <Network size={32} style={{ margin: "0 auto 0.75rem", opacity: 0.4 }} />
            <div style={{ fontSize: "1rem", color: "var(--color-text)", marginBottom: "0.5rem" }}>
              Graph endpoint not implemented yet
            </div>
            <div style={{ fontSize: "0.875rem", maxWidth: "48ch" }}>
              Add the Slice 3 graph/data endpoint in Axiom API, then this page will render Query, Finding, and Source nodes.
            </div>
          </div>
        </div>
      )}

      {hasGraph && (
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
          <ForceGraph2D
            graphData={graphData}
            nodeLabel={(node) => {
              const n = node as ForceNode;
              return `${n.label ?? "Node"}${n.type ? ` (${n.type})` : ""}`;
            }}
            nodeAutoColorBy="type"
            linkLabel={(link) => {
              const l = link as ForceLink;
              return l.type ?? "";
            }}
            backgroundColor="#141416"
          />
        </div>
      )}
    </Shell>
  );
}
