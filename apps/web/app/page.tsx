"use client";

import Link from "next/link";
import { useEffect, useState, useCallback, useMemo } from "react";
import Shell from "@/components/Shell";
import MarkdownRenderer from "@/components/MarkdownRenderer";
import SourcesPanel from "@/components/SourcesPanel";
import { type Job, fetchJobs, createJob } from "@/lib/api";
import { useResearchStream } from "./useResearchStream";
import {
  Loader2,
  Send,
  ChevronRight,
  Clock,
  CheckCircle2,
  XCircle,
  Zap,
} from "lucide-react";

type ReferenceItem = {
  title: string;
  url: string;
  snippet: string;
};

type HealthService = {
  name: string;
  ok?: boolean;
  detail?: string;
  status?: string;
};

type HealthState = {
  status?: string;
  services?: HealthService[];
};

const statusIcon: Record<string, React.ReactNode> = {
  queued: <Clock size={14} style={{ color: "var(--color-text-muted)" }} />,
  running: <Loader2 size={14} className="animate-spin" style={{ color: "var(--color-primary)" }} />,
  done: <CheckCircle2 size={14} style={{ color: "#6daa45" }} />,
  error: <XCircle size={14} style={{ color: "#a12c7b" }} />,
};

function formatElapsed(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const s = totalSeconds % 60;
  const m = Math.floor(totalSeconds / 60);
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

function getJobQuestion(job: Job): string {
  return job.question ?? job.query ?? "(untitled job)";
}

function extractReferences(job: Job | null, report: string): ReferenceItem[] {
  const findingRefs = (job?.findings ?? [])
    .flatMap((finding) => finding.results ?? [])
    .filter((r) => r?.url || r?.title)
    .map((r) => ({
      title: r.title?.trim() || r.url?.trim() || "Untitled source",
      url: r.url?.trim() || "",
      snippet: r.snippet?.trim() || "",
    }));

  const directRefs = [...(job?.references ?? []), ...(job?.sources ?? [])]
    .filter((r) => r?.url || r?.title)
    .map((r) => ({
      title: r.title?.trim() || r.url?.trim() || "Untitled source",
      url: r.url?.trim() || "",
      snippet: r.snippet?.trim() || "",
    }));

  const combined = findingRefs.length > 0 ? findingRefs : directRefs;
  if (combined.length > 0) {
    const seen = new Set<string>();
    return combined.filter((r) => {
      const key = `${r.title}|${r.url}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  const matches = Array.from(
    report.matchAll(/https?:\/\/[^\s)\]]+/g),
    (m) => m[0].replace(/[.,;]+$/, ""),
  );

  const seen = new Set<string>();
  return matches
    .filter((url) => {
      if (seen.has(url)) return false;
      seen.add(url);
      return true;
    })
    .map((url) => ({ title: url, url, snippet: "" }));
}

export default function DashboardPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [query, setQuery] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const [health, setHealth] = useState<HealthState | null>(null);
  const [healthError, setHealthError] = useState("");
  const [refreshTick, setRefreshTick] = useState(0);

  const stream = useResearchStream(activeJobId);

  const loadJobs = useCallback(async () => {
    try {
      const data = await fetchJobs();
      data.sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      );
      setJobs(data);
    } catch (err) {
      console.error("[dashboard] Failed to fetch jobs", err);
    }
  }, []);

  useEffect(() => {
    const interval = window.setInterval(() => {
      setRefreshTick((tick) => tick + 1);
    }, 5000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    let cancelled = false;

    const loadHealth = async () => {
      try {
        const res = await fetch("/api/health", { cache: "no-store" });
        if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
        const data = await res.json();
        if (!cancelled) {
          setHealth(data);
          setHealthError("");
        }
      } catch (err) {
        if (!cancelled) {
          setHealthError(err instanceof Error ? err.message : String(err));
        }
      }
    };

    void loadHealth();
    const interval = window.setInterval(() => {
      void loadHealth();
    }, 15000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    const id = window.setTimeout(() => {
      void loadJobs();
    }, 0);
    return () => window.clearTimeout(id);
  }, [loadJobs, refreshTick]);

  useEffect(() => {
    if (!startedAt || !activeJobId) return;
    const id = window.setInterval(() => {
      setNow(Date.now());
    }, 1000);
    return () => window.clearInterval(id);
  }, [startedAt, activeJobId]);

  useEffect(() => {
    if (stream.phase !== "done" && stream.phase !== "error") return;
    const id1 = window.setTimeout(() => { void loadJobs(); }, 0);
    const id2 = window.setTimeout(() => { void loadJobs(); }, 600);
    return () => {
      window.clearTimeout(id1);
      window.clearTimeout(id2);
    };
  }, [stream.phase, loadJobs]);

  const handleOpenJob = useCallback((job: Job) => {
    setActiveJobId(job.id);
    if (job.status === "queued" || job.status === "running") {
      setStartedAt(Date.now());
    } else {
      setStartedAt(
        job.created_at ? new Date(job.created_at).getTime() : null,
      );
    }
    setSubmitError("");
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setSubmitting(true);
    setSubmitError("");

    try {
      const job = await createJob(query.trim());
      setQuery("");
      setActiveJobId(job.id);
      setStartedAt(Date.now());
      await loadJobs();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  const activeJob = useMemo(
    () => jobs.find((j) => j.id === activeJobId) ?? null,
    [jobs, activeJobId],
  );

  const report =
    stream.text ||
    activeJob?.report ||
    "";

  const error =
    stream.errorMessage ||
    activeJob?.error ||
    submitError;

  const elapsedMs = startedAt ? Math.max(0, now - startedAt) : 0;

  const formatElapsedSeconds = (totalSeconds: number): string => {
    if (!Number.isFinite(totalSeconds) || totalSeconds < 0) return "0.0s";
    if (totalSeconds < 60) return `${totalSeconds.toFixed(1)}s`;
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}m ${seconds.toFixed(1)}s`;
  };

  const displayElapsed =
    stream.phase === "done" && typeof stream.elapsedSeconds === "number"
      ? formatElapsedSeconds(stream.elapsedSeconds)
      : startedAt
        ? formatElapsedSeconds(elapsedMs / 1000)
        : null;

  const references = useMemo(
    () => extractReferences(activeJob, report),
    [activeJob, report],
  );

  const liveReferenceCount = stream.sources.length || references.length;
  const displayAxiomCreated =
    stream.phase === "done"
      ? Boolean(activeJob?.axiom_id)
      : Boolean(activeJob?.axiom_id);

  return (
    <Shell>
      <div style={{ maxWidth: "1100px" }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
            gap: "0.75rem",
            marginBottom: "1rem",
          }}
        >
          {[
            {
              label: "API",
              value: health?.status ?? (healthError ? "unavailable" : "checking"),
              tone:
                health?.status === "healthy"
                  ? "var(--color-success)"
                  : healthError
                    ? "var(--color-error)"
                    : "var(--color-warning)",
            },
            ...["ollama", "searxng", "neo4j", "valkey"].map((name) => {
              const raw = health?.services?.find((service) => service.name === name);
              const value =
                raw?.status ??
                (typeof raw?.ok === "boolean"
                  ? (raw.ok ? "healthy" : "unhealthy")
                  : "unknown");
              return {
                label: name,
                value,
                tone:
                  value === "healthy"
                    ? "var(--color-success)"
                    : value === "unknown"
                      ? "var(--color-warning)"
                      : "var(--color-error)",
              };
            }),
          ].map((item) => (
            <div
              key={item.label}
              style={{
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-lg)",
                padding: "0.8rem 0.9rem",
              }}
            >
              <div
                style={{
                  fontSize: "0.72rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  color: "var(--color-text-muted)",
                  marginBottom: "0.35rem",
                }}
              >
                {item.label}
              </div>
              <div
                style={{
                  fontSize: "0.95rem",
                  fontWeight: 700,
                  color: item.tone,
                  textTransform: "capitalize",
                }}
              >
                {item.value}
              </div>
            </div>
          ))}
        </div>

        {healthError && (
          <div
            style={{
              marginBottom: "1rem",
              padding: "0.7rem 0.9rem",
              borderRadius: "var(--radius-md)",
              border: "1px solid color-mix(in oklab, var(--color-error) 40%, transparent)",
              background: "color-mix(in oklab, var(--color-error) 10%, transparent)",
              color: "var(--color-error)",
              fontSize: "0.84rem",
            }}
          >
            Health endpoint unavailable: {healthError}
          </div>
        )}

        <h1
          style={{
            fontSize: "1.5rem",
            fontWeight: 700,
            marginBottom: "1.5rem",
            color: "var(--color-text)",
          }}
        >
          Dashboard
        </h1>

        <form
          onSubmit={handleSubmit}
          style={{
            display: "flex",
            gap: "0.75rem",
            marginBottom: "2rem",
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-lg)",
            padding: "1rem",
          }}
        >
          <input
            type="text"
            placeholder="Ask a research question…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={submitting}
            style={{
              flex: 1,
              background: "var(--color-surface-2)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
              padding: "0.625rem 0.875rem",
              color: "var(--color-text)",
              fontSize: "0.9375rem",
              outline: "none",
            }}
          />
          <button
            type="submit"
            disabled={submitting || !query.trim()}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.375rem",
              padding: "0.625rem 1.25rem",
              background: submitting ? "var(--color-border)" : "var(--color-primary)",
              color: "#fff",
              border: "none",
              borderRadius: "var(--radius-md)",
              fontWeight: 600,
              fontSize: "0.875rem",
              cursor: submitting ? "not-allowed" : "pointer",
            }}
          >
            {submitting ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
            {submitting ? "Queuing…" : "Run"}
          </button>
        </form>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: "1.5rem",
            alignItems: "start",
          }}
        >
          <div style={{ minWidth: 0 }}>
            <h2
              style={{
                fontSize: "0.8rem",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                color: "var(--color-text-muted)",
                marginBottom: "0.75rem",
              }}
            >
              Queue
            </h2>

            {jobs.length === 0 && (
              <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem" }}>
                No jobs yet.
              </p>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: "0.375rem" }}>
              {jobs.map((job) => (
                <button
                  key={job.id}
                  onClick={() => handleOpenJob(job)}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "0.5rem",
                    padding: "0.625rem 0.75rem",
                    background: activeJobId === job.id ? "oklch(from var(--color-primary) l c h / 0.1)" : "var(--color-surface)",
                    border: `1px solid ${activeJobId === job.id ? "var(--color-primary)" : "var(--color-border)"}`,
                    borderRadius: "var(--radius-md)",
                    textAlign: "left",
                    cursor: "pointer",
                    transition: "border-color 180ms, background 180ms",
                  }}
                >
                  <span style={{ marginTop: "0.125rem", flexShrink: 0 }}>{statusIcon[job.status]}</span>
                  <span
                    style={{
                      fontSize: "0.8125rem",
                      color: "var(--color-text)",
                      lineHeight: 1.4,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      maxWidth: "180px",
                    }}
                    title={getJobQuestion(job)}
                  >
                    {getJobQuestion(job)}
                  </span>
                  <ChevronRight size={13} style={{ marginLeft: "auto", color: "var(--color-text-muted)", flexShrink: 0 }} />
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: "grid", gap: "1rem" }}>
            {!activeJobId && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "300px",
                  color: "var(--color-text-muted)",
                  gap: "0.75rem",
                }}
              >
                <Zap size={32} style={{ opacity: 0.3 }} />
                <p style={{ fontSize: "0.875rem" }}>Submit a query or select a job to see output.</p>
              </div>
            )}

            {activeJobId && (
              <>
                <div
                  style={{
                    display: "flex",
                    gap: "0.75rem",
                    flexWrap: "wrap",
                    color: "var(--color-text-muted)",
                    fontSize: "0.82rem",
                  }}
                >
                  <span>Status: {stream.phase !== "idle" ? stream.phase : (activeJob?.status ?? "unknown")}</span>
                  <span>Elapsed: {formatElapsed(elapsedMs)}</span>
                  <span>Refs: {liveReferenceCount}</span>
                  {stream.currentQuery && <span>Searching: {stream.currentQuery}</span>}
                </div>

                <div
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: "0.5rem",
                    marginTop: "-0.25rem",
                  }}
                >
                  <Link
                    href="/graph"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "0.35rem",
                      padding: "0.45rem 0.7rem",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid var(--color-border)",
                      background: "var(--color-surface-2)",
                      color: "var(--color-text)",
                      fontSize: "0.82rem",
                      fontWeight: 600,
                      textDecoration: "none",
                    }}
                  >
                    Open graph
                    <ChevronRight size={14} />
                  </Link>
                  <Link
                    href="/axioms"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "0.35rem",
                      padding: "0.45rem 0.7rem",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid var(--color-border)",
                      background: "var(--color-surface-2)",
                      color: "var(--color-text)",
                      fontSize: "0.82rem",
                      fontWeight: 600,
                      textDecoration: "none",
                    }}
                  >
                    Open axioms
                    <ChevronRight size={14} />
                  </Link>
                  <Link
                    href="/council"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "0.35rem",
                      padding: "0.45rem 0.7rem",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid var(--color-border)",
                      background: "var(--color-surface-2)",
                      color: "var(--color-text)",
                      fontSize: "0.82rem",
                      fontWeight: 600,
                      textDecoration: "none",
                    }}
                  >
                    Open council
                    <ChevronRight size={14} />
                  </Link>
                  <Link
                    href="/settings"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "0.35rem",
                      padding: "0.45rem 0.7rem",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid var(--color-border)",
                      background: "var(--color-surface-2)",
                      color: "var(--color-text)",
                      fontSize: "0.82rem",
                      fontWeight: 600,
                      textDecoration: "none",
                    }}
                  >
                    Settings
                    <ChevronRight size={14} />
                  </Link>
                </div>

                {(stream.phase !== "idle" || activeJob?.status === "running" || activeJob?.status === "queued") && (
                  <div
                    style={{
                      background: "var(--color-surface)",
                      border: "1px solid var(--color-border)",
                      borderRadius: "var(--radius-lg)",
                      padding: "0.875rem 1rem",
                    }}
                  >
                    <div
                      style={{
                        fontSize: "0.8rem",
                        fontWeight: 600,
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                        color: "var(--color-text-muted)",
                        marginBottom: "0.5rem",
                      }}
                    >
                      Live Stream
                    </div>
                    <div style={{ display: "grid", gap: "0.45rem", fontSize: "0.86rem" }}>
                      <div style={{ color: "var(--color-text)" }}>
                        Phase: <strong>{stream.phase}</strong>
                      </div>
                      {stream.currentQuery && (
                        <div style={{ color: "var(--color-text-muted)" }}>
                          Searching: {stream.currentQuery}
                        </div>
                      )}
                      {stream.phase === "generating" && (
                        <div style={{ color: "var(--color-primary)", fontWeight: 600 }}>
                          Synthesizing live answer…
                        </div>
                      )}
                      {stream.findingCount !== null && (
                        <div style={{ color: "var(--color-text-muted)" }}>
                          Findings: {stream.findingCount}
                        </div>
                      )}
                      {displayElapsed && (
                        <div style={{ color: "var(--color-text-muted)" }}>
                          Elapsed: {displayElapsed}
                        </div>
                      )}
                      {displayAxiomCreated && (
                        <div style={{ color: "var(--color-success)", fontWeight: 600 }}>
                          Axiom created
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {stream.sources.length > 0 && (
                  <SourcesPanel
                    title="Live Sources"
                    sources={stream.sources.map((s) => ({
                      title: s.title,
                      url: s.url,
                      snippet: "",
                    }))}
                  />
                )}

                {error && (
                  <div
                    style={{
                      background: "rgba(127,29,29,0.25)",
                      border: "1px solid rgba(248,113,113,0.35)",
                      borderRadius: "var(--radius-md)",
                      padding: "0.75rem 1rem",
                      color: "#fda4af",
                      fontSize: "0.875rem",
                    }}
                  >
                    {error}
                  </div>
                )}

                {report && (
                  <div>
                    <h2
                      style={{
                        fontSize: "0.8rem",
                        fontWeight: 600,
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                        color: "var(--color-text-muted)",
                        marginBottom: "0.5rem",
                      }}
                    >
                      Report
                    </h2>
                    <div
                      style={{
                        background: "var(--color-surface)",
                        border: "1px solid var(--color-border)",
                        borderRadius: "var(--radius-lg)",
                        padding: "1.5rem",
                        lineHeight: 1.75,
                        color: "var(--color-text)",
                      }}
                    >
                      <MarkdownRenderer content={report} />
                    </div>
                  </div>
                )}

                {references.length > 0 && (
                  <SourcesPanel title="References" sources={references} />
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </Shell>
  );
}
