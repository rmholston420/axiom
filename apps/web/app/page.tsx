"use client";

import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import Shell from "@/components/Shell";
import { type Job, fetchJobs, createJob } from "@/lib/api";
import {
  Loader2,
  Send,
  ChevronRight,
  Clock,
  CheckCircle2,
  XCircle,
  Zap,
  Link2,
} from "lucide-react";

type ReferenceItem = {
  title: string;
  url: string;
  snippet: string;
};

type LiveFinding = {
  index: number;
  subQuery: string;
  summary: string;
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
  const [events, setEvents] = useState<string[]>([]);
  const [streamReport, setStreamReport] = useState<string>("");
  const [streamError, setStreamError] = useState<string>("");
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const [refreshTick, setRefreshTick] = useState(0);

  const eventsRef = useRef<HTMLDivElement>(null);
  const sseRef = useRef<EventSource | null>(null);

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
    if (eventsRef.current) {
      eventsRef.current.scrollTop = eventsRef.current.scrollHeight;
    }
  }, [events]);

  useEffect(() => {
    return () => {
      sseRef.current?.close();
    };
  }, []);

  const openStream = useCallback((jobId: string) => {
    sseRef.current?.close();
    setEvents([]);
    setStreamReport("");
    setStreamError("");
    setActiveJobId(jobId);
    setStartedAt(Date.now());
    setNow(Date.now());

    const es = new EventSource(`/api/jobs/${jobId}/stream`);
    sseRef.current = es;


    es.onmessage = (e) => {
      const data = e.data as string;

      if (data === "[DONE]" || data === "\"[DONE]\"") {
        es.close();
        void loadJobs().then(() => {
          setTimeout(() => {
            void loadJobs();
          }, 600);
        });
        return;
      }

      try {
        const parsed = JSON.parse(data);
        if (parsed.type === "event") setEvents((prev) => [...prev, parsed.message]);
        if (parsed.type === "report") setStreamReport(parsed.content);
        if (parsed.type === "error") setStreamError(parsed.message);
        if (parsed.type === "finding" && parsed.data) {
          const item: LiveFinding = {
            index: Number(parsed.data.index ?? 0),
            subQuery: String(parsed.data.sub_query ?? "").trim(),
            summary: String(parsed.data.summary ?? "").trim(),
          };
          if (item.index > 0) {
            setEvents((prev) => [
              ...prev,
              `Finding ${item.index}: ${item.subQuery || "sub-query"} — ${item.summary || "update received"}`,
            ]);
          }
        }
      } catch {
        setEvents((prev) => [...prev, data]);
      }
    };

    es.onerror = () => {
      es.close();
      void loadJobs().then(() => {
        setTimeout(() => {
          void loadJobs();
        }, 600);
      });
    };
  }, [loadJobs]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setSubmitting(true);
    setSubmitError("");

    try {
      const job = await createJob(query.trim());
      setQuery("");
      await loadJobs();
      openStream(job.id);
    } catch (err) {
      setStreamError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  const activeJob = useMemo(
    () => jobs.find((j) => j.id === activeJobId) ?? null,
    [jobs, activeJobId],
  );

  const report = activeJob?.report ?? streamReport;
  const error = activeJob?.error ?? streamError;


  const isActiveJobRunning = Boolean(
    startedAt &&
    activeJob &&
    (activeJob.status === "queued" || activeJob.status === "running"),
  );

  const elapsedMs = startedAt ? Math.max(0, now - startedAt) : 0;

  const references = useMemo(
    () => extractReferences(activeJob, report),
    [activeJob, report],
  );

  return (
    <Shell>
      <div style={{ maxWidth: "1100px" }}>
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

        <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: "1.5rem" }}>
          <div>
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
                  onClick={() => {
                    setActiveJobId(job.id);
                    setReport(job.report ?? "");
                    setEvents([]);
                    setError(job.error ?? "");
                    if (job.status === "queued" || job.status === "running") {
                      openStream(job.id);
                    } else {
                      sseRef.current?.close();
                      setStartedAt(null);
                    }
                  }}
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
                  <span>Status: {activeJob?.status ?? "unknown"}</span>
                  <span>Elapsed: {formatElapsed(elapsedMs)}</span>
                  <span>Refs: {references.length}</span>
                </div>

                {(events.length > 0 || activeJob?.status === "running" || activeJob?.status === "queued") && (
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
                      Live Stream
                    </h2>
                    <div
                      ref={eventsRef}
                      style={{
                        background: "var(--color-surface)",
                        border: "1px solid var(--color-border)",
                        borderRadius: "var(--radius-lg)",
                        padding: "0.875rem 1rem",
                        maxHeight: "180px",
                        overflowY: "auto",
                        fontFamily: "ui-monospace, monospace",
                        fontSize: "0.8rem",
                        lineHeight: 1.6,
                        color: "var(--color-text-muted)",
                      }}
                    >
                      {events.length === 0 && <span style={{ opacity: 0.5 }}>Waiting for events…</span>}
                      {events.map((ev, i) => (
                        <div key={i} style={{ marginBottom: "0.125rem" }}>
                          <span style={{ color: "var(--color-primary)", marginRight: "0.5rem" }}>›</span>
                          {ev}
                        </div>
                      ))}
                    </div>
                  </div>
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
                        fontSize: "0.9375rem",
                      }}
                    >
                      <ReactMarkdown>{report}</ReactMarkdown>
                    </div>
                  </div>
                )}

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
                    References
                  </h2>
                  <div
                    style={{
                      background: "var(--color-surface)",
                      border: "1px solid var(--color-border)",
                      borderRadius: "var(--radius-lg)",
                      padding: "1rem",
                    }}
                  >
                    {references.length === 0 ? (
                      <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem" }}>
                        No references surfaced for this job yet.
                      </p>
                    ) : (
                      <div style={{ display: "grid", gap: "0.75rem" }}>
                        {references.map((ref, idx) => (
                          <a
                            key={`${ref.url}-${idx}`}
                            href={ref.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                              display: "block",
                              padding: "0.75rem 0.875rem",
                              background: "var(--color-surface-2)",
                              border: "1px solid var(--color-border)",
                              borderRadius: "var(--radius-md)",
                              color: "var(--color-text)",
                              textDecoration: "none",
                            }}
                          >
                            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem" }}>
                              <Link2 size={14} style={{ color: "var(--color-primary)" }} />
                              <span style={{ fontSize: "0.9rem", fontWeight: 600, lineHeight: 1.4 }}>
                                {ref.title}
                              </span>
                            </div>
                            {ref.url && (
                              <div style={{ color: "var(--color-text-muted)", fontSize: "0.8rem", wordBreak: "break-all" }}>
                                {ref.url}
                              </div>
                            )}
                            {ref.snippet && (
                              <div style={{ color: "var(--color-text-muted)", fontSize: "0.82rem", marginTop: "0.35rem" }}>
                                {ref.snippet}
                              </div>
                            )}
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </Shell>
  );
}
