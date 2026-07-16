"use client";

import { useEffect, useState } from "react";
import { BookMarked, CheckCircle2, XCircle, Loader2, RefreshCw, AlertCircle, Filter, Copy, ThumbsUp, ThumbsDown } from "lucide-react";
import Shell from "@/components/Shell";
import { fetchAxioms, approveAxiom, type AxiomRecord } from "@/lib/api";

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



function ManualReviewBadge({ show }: { show?: boolean }) {
  if (!show) return null;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.25rem",
        fontSize: "0.7rem",
        fontWeight: 600,
        padding: "0.15rem 0.5rem",
        borderRadius: "var(--radius-full)",
        color: "var(--color-primary)",
        background: "color-mix(in oklab, var(--color-primary) 12%, transparent)",
        border: "1px solid color-mix(in oklab, var(--color-primary) 30%, transparent)",
      }}
    >
      Manual review
    </span>
  );
}

function EvaluationWarningBadge({ show }: { show?: boolean }) {
  if (!show) return null;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.25rem",
        fontSize: "0.7rem",
        fontWeight: 600,
        padding: "0.15rem 0.5rem",
        borderRadius: "var(--radius-full)",
        color: "var(--color-warning)",
        background: "color-mix(in oklab, var(--color-warning) 12%, transparent)",
        border: "1px solid color-mix(in oklab, var(--color-warning) 30%, transparent)",
      }}
    >
      <AlertCircle size={10} /> Evaluation warning
    </span>
  );
}

function ApproveButtons({
  axiom,
  onUpdate,
}: {
  axiom: AxiomRecord;
  onUpdate: (id: string, approved: boolean) => void;
}) {
  const [busy, setBusy] = useState(false);
  const id = axiom.id ?? axiom.axiom_id ?? "";

  async function toggle(newApproved: boolean) {
    if (!id || busy) return;
    setBusy(true);
    try {
      await approveAxiom(id, newApproved);
      onUpdate(id, newApproved);
    } catch {
      // silent — the badge won't update, user can retry
    } finally {
      setBusy(false);
    }
  }

  const isApproved = axiom.approved === true;
  const isPending = axiom.approved !== true;

  return (
    <div style={{ display: "flex", gap: "0.375rem", alignItems: "center" }}>
      <button
        type="button"
        disabled={busy || isApproved}
        onClick={() => void toggle(true)}
        title="Approve this axiom"
        aria-label="Approve axiom"
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.25rem",
          padding: "0.25rem 0.625rem",
          fontSize: "0.75rem",
          fontWeight: 600,
          borderRadius: "var(--radius-md)",
          border: "1px solid color-mix(in oklab, var(--color-success) 35%, transparent)",
          background: isApproved
            ? "color-mix(in oklab, var(--color-success) 18%, transparent)"
            : "var(--color-surface)",
          color: isApproved ? "var(--color-success)" : "var(--color-text-muted)",
          cursor: isApproved ? "default" : "pointer",
          opacity: busy ? 0.6 : 1,
          transition: "background 180ms, color 180ms",
        }}
      >
        {busy ? <Loader2 size={11} style={{ animation: "spin 1s linear infinite" }} /> : <ThumbsUp size={11} />}
        Approve
      </button>
      <button
        type="button"
        disabled={busy || isPending}
        onClick={() => void toggle(false)}
        title="Reject this axiom"
        aria-label="Reject axiom"
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.25rem",
          padding: "0.25rem 0.625rem",
          fontSize: "0.75rem",
          fontWeight: 600,
          borderRadius: "var(--radius-md)",
          border: "1px solid color-mix(in oklab, var(--color-error) 35%, transparent)",
          background: isPending
            ? "color-mix(in oklab, var(--color-error) 14%, transparent)"
            : "var(--color-surface)",
          color: isPending ? "var(--color-error)" : "var(--color-text-muted)",
          cursor: isPending ? "default" : "pointer",
          opacity: busy ? 0.6 : 1,
          transition: "background 180ms, color 180ms",
        }}
      >
        {busy ? <Loader2 size={11} style={{ animation: "spin 1s linear infinite" }} /> : <ThumbsDown size={11} />}
        Reject
      </button>
    </div>
  );
}

export default function AxiomsPage() {
  const [axioms, setAxioms] = useState<AxiomRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [limit, setLimit] = useState(25);
  const [showWarningsOnly, setShowWarningsOnly] = useState(false);
  const [sortOrder, setSortOrder] = useState<"desc" | "asc">("desc");
  const [copyMessage, setCopyMessage] = useState("");

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

  function handleApprovalUpdate(id: string, approved: boolean) {
    setAxioms((prev) =>
      prev.map((a) =>
        (a.id === id || a.axiom_id === id)
          ? { ...a, approved, eval_reason: approved ? "Manually approved" : "Manually rejected" }
          : a
      )
    );
  }

  const warningAxioms = axioms.filter((a) => a.evaluation_warning === true);
  const warningCount = warningAxioms.length;
  const visibleAxioms = (showWarningsOnly ? warningAxioms : axioms).slice().sort((a, b) => {
    const at = new Date(a.created_at).getTime();
    const bt = new Date(b.created_at).getTime();
    return sortOrder === "desc" ? bt - at : at - bt;
  });

  async function copyWarningExport() {
    const exportRows = warningAxioms.slice().sort((a, b) => {
      const at = new Date(a.created_at).getTime();
      const bt = new Date(b.created_at).getTime();
      return sortOrder === "desc" ? bt - at : at - bt;
    });

    const payload = [
      `Warning-state axioms review export (${exportRows.length})`,
      `Sort order: ${sortOrder === "desc" ? "Newest first" : "Oldest first"}`,
      "",
      ...exportRows.map((axiom, idx) => {
        const pct = Math.round((axiom.confidence ?? 0) * 100);
        return [
          `${idx + 1}. ${axiom.label || `Axiom #${idx + 1}`}`,
          `Statement: ${axiom.statement ?? ""}`,
          `Confidence: ${pct}%`,
          `Approved: ${axiom.approved === true ? "true" : "false"}`,
          `Evaluation warning: ${axiom.evaluation_warning === true ? "true" : "false"}`,
          `Eval note: ${axiom.evaluation_warning ? "Model evaluation failed, treating as approved" : (axiom.eval_reason ?? "")}`,
          `Created: ${new Date(axiom.created_at).toLocaleString()}`,
          `Persisted: ${axiom.persisted ? "true" : "false"}`
        ].join("\n");
      }),
    ].join("\n\n");

    try {
      await navigator.clipboard.writeText(payload);
      setCopyMessage(`Copied ${exportRows.length} warning-state axioms`);
      window.setTimeout(() => setCopyMessage(""), 2500);
    } catch (err) {
      setCopyMessage(err instanceof Error ? err.message : "Copy failed");
      window.setTimeout(() => setCopyMessage(""), 3000);
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

          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
            <button
              type="button"
              onClick={() => setShowWarningsOnly((v) => !v)}
              aria-pressed={showWarningsOnly}
              title="Toggle warning-only curation view"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.375rem",
                padding: "0.4rem 0.875rem",
                background: showWarningsOnly
                  ? "color-mix(in oklab, var(--color-warning) 12%, transparent)"
                  : "var(--color-surface)",
                border: showWarningsOnly
                  ? "1px solid color-mix(in oklab, var(--color-warning) 30%, transparent)"
                  : "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
                color: showWarningsOnly ? "var(--color-warning)" : "var(--color-text-muted)",
                fontSize: "0.8125rem",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              <Filter size={13} />
              {showWarningsOnly ? "Showing warnings only" : "Show warnings only"}
            </button>

            <select
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value as "desc" | "asc")}
              title="Sort axioms by created time"
              style={{
                background: "var(--color-surface)",
                color: "var(--color-text)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
                padding: "0.4rem 0.75rem",
                fontSize: "0.85rem",
              }}
            >
              <option value="desc">Newest first</option>
              <option value="asc">Oldest first</option>
            </select>

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
              type="button"
              onClick={() => void copyWarningExport()}
              disabled={warningCount === 0}
              title="Copy warning-state axioms for review"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.375rem",
                padding: "0.4rem 0.875rem",
                background: warningCount > 0
                  ? "color-mix(in oklab, var(--color-primary) 10%, transparent)"
                  : "var(--color-surface)",
                border: warningCount > 0
                  ? "1px solid color-mix(in oklab, var(--color-primary) 30%, transparent)"
                  : "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
                color: warningCount > 0 ? "var(--color-primary)" : "var(--color-text-muted)",
                fontSize: "0.8125rem",
                fontWeight: 600,
                cursor: warningCount > 0 ? "pointer" : "not-allowed",
                opacity: warningCount === 0 ? 0.5 : 1,
              }}
            >
              <Copy size={13} />
              {copyMessage || (warningCount > 0 ? `Export ${warningCount} warnings` : "No warnings")}
            </button>

            <button
              type="button"
              onClick={() => void load(limit)}
              disabled={loading}
              title="Refresh axioms"
              aria-label="Refresh"
              style={{
                display: "flex",
                alignItems: "center",
                padding: "0.4rem",
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
                color: "var(--color-text-muted)",
                cursor: "pointer",
              }}
            >
              {loading ? (
                <Loader2 size={15} style={{ animation: "spin 1s linear infinite" }} />
              ) : (
                <RefreshCw size={15} />
              )}
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
            { label: "Total", value: visibleAxioms.length, color: "var(--color-primary)" },
            { label: "Approved", value: visibleAxioms.filter((a) => a.approved === true).length, color: "var(--color-success)" },
            { label: "Pending", value: visibleAxioms.filter((a) => a.approved !== true).length, color: "var(--color-text-muted)" },
            { label: "Warnings", value: warningCount, color: "var(--color-warning)" },
            {
              label: "Avg Confidence",
              value:
                visibleAxioms.length > 0
                  ? Math.round((visibleAxioms.reduce((s, a) => s + (a.confidence ?? 0), 0) / visibleAxioms.length) * 100) + "%"
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
              background: "color-mix(in oklab, var(--color-error) 10%, transparent)",
              border: "1px solid color-mix(in oklab, var(--color-error) 30%, transparent)",
              color: "var(--color-error)",
              borderRadius: "var(--radius-md)",
              padding: "0.75rem 1rem",
              marginBottom: "1rem",
              fontSize: "0.875rem",
            }}
          >
            {error}
          </div>
        )}

        {/* Empty */}
        {!loading && !error && visibleAxioms.length === 0 && (
          <div
            style={{
              textAlign: "center",
              padding: "3rem 1rem",
              color: "var(--color-text-muted)",
              fontSize: "0.9rem",
            }}
          >
            No axioms found. Run the Axiomatizer to generate some.
          </div>
        )}

        {/* Axiom cards */}
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {visibleAxioms.map((axiom, idx) => {
            const axiomId = axiom.id ?? axiom.axiom_id ?? String(idx);
            return (
              <div
                key={axiomId}
                style={{
                  background: "var(--color-surface)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-lg)",
                  padding: "1rem 1.25rem",
                  boxShadow: "var(--shadow-sm)",
                }}
              >
                {/* Card header */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    justifyContent: "space-between",
                    gap: "1rem",
                    flexWrap: "wrap",
                    marginBottom: "0.5rem",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap", flex: 1, minWidth: 0 }}>
                    <span
                      style={{
                        fontWeight: 700,
                        fontSize: "0.9rem",
                        color: "var(--color-text)",
                        wordBreak: "break-word",
                      }}
                    >
                      {axiom.label || `Axiom #${idx + 1}`}
                    </span>
                    <ConfidenceBadge value={axiom.confidence ?? 0} />
                    <ApprovalBadge approved={axiom.approved} />
                    <EvaluationWarningBadge show={axiom.evaluation_warning} />
                    <ManualReviewBadge show={(axiom.eval_reason ?? "").startsWith("Manually ")} />
                  </div>

                  {/* Approve / Reject buttons */}
                  <ApproveButtons axiom={axiom} onUpdate={handleApprovalUpdate} />
                </div>

                {/* Statement */}
                <p
                  style={{
                    fontSize: "0.875rem",
                    color: "var(--color-text)",
                    margin: "0 0 0.375rem",
                    lineHeight: 1.55,
                  }}
                >
                  {axiom.statement}
                </p>

                {/* Justification */}
                {axiom.justification && (
                  <p
                    style={{
                      fontSize: "0.8125rem",
                      color: "var(--color-text-muted)",
                      margin: "0 0 0.375rem",
                      fontStyle: "italic",
                      lineHeight: 1.5,
                    }}
                  >
                    {axiom.justification}
                  </p>
                )}

                {/* Eval reason */}
                {axiom.eval_reason && (
                  <p
                    style={{
                      fontSize: "0.775rem",
                      color: "var(--color-text-faint)",
                      margin: "0 0 0.375rem",
                    }}
                  >
                    {axiom.eval_reason}
                  </p>
                )}

                {/* Timestamp */}
                <p
                  style={{
                    fontSize: "0.75rem",
                    color: "var(--color-text-faint)",
                    margin: 0,
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {new Date(axiom.created_at).toLocaleString()}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </Shell>
  );
}
