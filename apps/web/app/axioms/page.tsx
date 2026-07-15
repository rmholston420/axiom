"use client";

import { useEffect, useState } from "react";
import { BookMarked, CheckCircle2, XCircle, Loader2, RefreshCw, AlertCircle } from "lucide-react";
import Shell from "@/components/Shell";
import { fetchAxioms, type AxiomRecord } from "@/lib/api";

function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 80 ? "var(--color-success)" :
    pct >= 50 ? "var(--color-warning)" :
    "var(--color-error)";
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.25rem",
        fontSize: "0.75rem",
        fontWeight: 600,
        padding: "0.2rem 0.55rem",
        borderRadius: "var(--radius-full)",
        color,
        background: `color-mix(in oklab, ${color} 14%, transparent)`,
        border: `1px solid color-mix(in oklab, ${color} 35%, transparent)`,
        fontVariantNumeric: "tabular-nums",
      }}
    >
      {pct}%
    </span>
  );
}

function ApprovalBadge({ approved }: { approved?: boolean }) {
  if (approved === undefined) return null;
  return approved ? (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.25rem",
        fontSize: "0.7rem",
        fontWeight: 600,
        padding: "0.15rem 0.5rem",
        borderRadius: "var(--radius-full)",
        color: "var(--color-success)",
        background: "color-mix(in oklab, var(--color-success) 12%, transparent)",
        border: "1px solid color-mix(in oklab, var(--color-success) 30%, transparent)",
      }}
    >
      <CheckCircle2 size={10} /> Approved
    </span>
  ) : (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.25rem",
        fontSize: "0.7rem",
        fontWeight: 600,
        padding: "0.15rem 0.5rem",
        borderRadius: "var(--radius-full)",
        color: "var(--color-text-muted)",
        background: "var(--color-surface-offset)",
        border: "1px solid var(--color-border)",
      }}
    >
      <XCircle size={10} /> Pending
    </span>
  );
}

export default function AxiomsPage() {
  const [axioms, setAxioms] = useState<AxiomRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [limit, setLimit] = useState(25);

  async function load(n: number) {
    setLoading(true);
    setError("");
    try {
      const data = await fetchAxioms(n);
      setAxioms(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      setLoading(true);
      setError("");
      try {
        const data = await fetchAxioms(limit);
        if (!cancelled) {
          setAxioms(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void run();

    return () => {
      cancelled = true;
    };
  }, [limit]);

  return (
    <Shell>
      <div style={{ maxWidth: "var(--content-wide)" }}>
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "1.5rem",
            flexWrap: "wrap",
            gap: "1rem",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <BookMarked size={20} style={{ color: "var(--color-primary)" }} />
            <div>
              <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--color-text)", margin: 0 }}>
                Axioms
              </h1>
              <p style={{ fontSize: "0.85rem", color: "var(--color-text-muted)", margin: 0 }}>
                Knowledge statements extracted and evaluated by the Axiomatizer.
              </p>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              style={{
                background: "var(--color-surface)",
                color: "var(--color-text)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
                padding: "0.4rem 0.75rem",
                fontSize: "0.85rem",
              }}
            >
              {[25, 50, 100, 200].map((n) => (
                <option key={n} value={n}>Show {n}</option>
              ))}
            </select>

            <button
              onClick={() => void load(limit)}
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
        </div>

        {/* Stats bar */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
            gap: "0.75rem",
            marginBottom: "1.25rem",
          }}
        >
          {[
            { label: "Total", value: axioms.length, color: "var(--color-primary)" },
            { label: "Approved", value: axioms.filter((a) => a.approved === true).length, color: "var(--color-success)" },
            { label: "Pending", value: axioms.filter((a) => a.approved !== true).length, color: "var(--color-text-muted)" },
            {
              label: "Avg Confidence",
              value:
                axioms.length > 0
                  ? Math.round((axioms.reduce((s, a) => s + (a.confidence ?? 0), 0) / axioms.length) * 100) + "%"
                  : "—",
              color: "var(--color-warning)",
            },
          ].map(({ label, value, color }) => (
            <div
              key={label}
              style={{
                padding: "0.9rem 1rem",
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-lg)",
              }}
            >
              <div style={{ fontSize: "0.7rem", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                {label}
              </div>
              <div style={{ fontSize: "1.5rem", fontWeight: 700, color, marginTop: "0.25rem", fontVariantNumeric: "tabular-nums" }}>
                {value}
              </div>
            </div>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              marginBottom: "1rem",
              padding: "0.875rem 1rem",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--color-error)",
              color: "var(--color-error)",
              background: "color-mix(in oklab, var(--color-error) 8%, transparent)",
              fontSize: "0.875rem",
            }}
          >
            <AlertCircle size={15} />
            {error}
          </div>
        )}

        {/* Loading skeleton */}
        {loading && axioms.length === 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                style={{
                  height: "100px",
                  borderRadius: "var(--radius-lg)",
                  background: "linear-gradient(90deg, var(--color-surface) 25%, var(--color-surface-offset) 50%, var(--color-surface) 75%)",
                  backgroundSize: "200% 100%",
                  animation: "shimmer 1.5s ease-in-out infinite",
                }}
              />
            ))}
          </div>
        )}

        {/* Empty state */}
        {!loading && axioms.length === 0 && !error && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              textAlign: "center",
              padding: "4rem 2rem",
              color: "var(--color-text-muted)",
            }}
          >
            <BookMarked size={40} style={{ marginBottom: "1rem", color: "var(--color-text-faint)" }} />
            <h3 style={{ color: "var(--color-text)", marginBottom: "0.5rem", fontSize: "1rem", fontWeight: 600 }}>
              No axioms yet
            </h3>
            <p style={{ maxWidth: "36ch", fontSize: "0.875rem" }}>
              Enable the Axiomatizer in Settings and run a research job to generate knowledge statements.
            </p>
          </div>
        )}

        {/* Axiom cards */}
        {axioms.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {axioms.map((axiom, idx) => {
              const id = axiom.axiom_id ?? axiom.id ?? String(idx);
              return (
                <div
                  key={id}
                  style={{
                    background: "var(--color-surface)",
                    border: "1px solid var(--color-border)",
                    borderRadius: "var(--radius-lg)",
                    padding: "1rem 1.25rem",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      justifyContent: "space-between",
                      gap: "0.75rem",
                      marginBottom: "0.6rem",
                      flexWrap: "wrap",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "0.8rem",
                        fontWeight: 600,
                        color: "var(--color-primary)",
                        letterSpacing: "0.04em",
                        textTransform: "uppercase",
                        fontVariantNumeric: "tabular-nums",
                      }}
                    >
                      {axiom.label || `Axiom #${idx + 1}`}
                    </span>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <ConfidenceBadge value={axiom.confidence ?? 0} />
                      <ApprovalBadge approved={axiom.approved} />
                    </div>
                  </div>

                  <p
                    style={{
                      fontSize: "0.9375rem",
                      color: "var(--color-text)",
                      lineHeight: 1.55,
                      margin: "0 0 0.5rem 0",
                    }}
                  >
                    {axiom.statement}
                  </p>

                  {axiom.justification && (
                    <p
                      style={{
                        fontSize: "0.825rem",
                        color: "var(--color-text-muted)",
                        lineHeight: 1.5,
                        margin: "0 0 0.5rem 0",
                      }}
                    >
                      {axiom.justification}
                    </p>
                  )}

                  {axiom.eval_reason && (
                    <p
                      style={{
                        fontSize: "0.775rem",
                        color: "var(--color-text-faint)",
                        fontStyle: "italic",
                        margin: 0,
                      }}
                    >
                      Eval: {axiom.eval_reason}
                    </p>
                  )}

                  <div
                    style={{
                      marginTop: "0.75rem",
                      paddingTop: "0.75rem",
                      borderTop: "1px solid var(--color-divider)",
                      fontSize: "0.7rem",
                      color: "var(--color-text-faint)",
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {new Date(axiom.created_at).toLocaleString()}
                    {axiom.persisted && (
                      <span style={{ marginLeft: "0.75rem", color: "var(--color-success)" }}>● persisted</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <style>{`
        @keyframes shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
      `}</style>
    </Shell>
  );
}
