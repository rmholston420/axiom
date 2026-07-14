"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import Shell from "@/components/Shell";
import { type Job, fetchJobs, createJob } from "@/lib/api";
import { Loader2, Send, ChevronRight, Clock, CheckCircle2, XCircle, Zap } from "lucide-react";

const statusIcon = {
  queued: <Clock size={14} style={{ color: "var(--color-text-muted)" }} />,
  running: <Loader2 size={14} className="animate-spin" style={{ color: "var(--color-primary)" }} />,
  done: <CheckCircle2 size={14} style={{ color: "#6daa45" }} />,
  error: <XCircle size={14} style={{ color: "#a12c7b" }} />,
} as const;

export default function DashboardPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [question, setQuestion] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [events, setEvents] = useState<string[]>([]);
  const [submitError, setSubmitError] = useState("");
  const [jobsError, setJobsError] = useState("");
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);

  const eventsRef = useRef<HTMLDivElement>(null);
  const pollerRef = useRef<number | null>(null);
  const mountedRef = useRef(false);
  const consecutiveFetchFailuresRef = useRef(0);

  const loadJobs = useCallback(async () => {
    try {
      const data = await fetchJobs();
      const sorted = data.sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );

      consecutiveFetchFailuresRef.current = 0;
      setJobs(sorted);
      setJobsError("");
      setHasLoadedOnce(true);

      if (!activeJobId && sorted.length > 0) {
        setActiveJobId(sorted[0].id);
      }
    } catch (err) {
      consecutiveFetchFailuresRef.current += 1;
      console.error("[dashboard] Failed to fetch jobs", err);

      if (consecutiveFetchFailuresRef.current >= 2) {
        setJobsError(err instanceof Error ? err.message : String(err));
      }
    }
  }, [activeJobId]);

  const startPolling = useCallback(() => {
    if (pollerRef.current !== null) return;

    pollerRef.current = window.setInterval(() => {
      void loadJobs();
    }, 2500);
  }, [loadJobs]);

  const stopPolling = useCallback(() => {
    if (pollerRef.current !== null) {
      window.clearInterval(pollerRef.current);
      pollerRef.current = null;
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;

    const timer = window.setTimeout(() => {
      if (mountedRef.current) {
        void loadJobs();
        startPolling();
      }
    }, 150);

    return () => {
      mountedRef.current = false;
      window.clearTimeout(timer);
      stopPolling();
    };
  }, [loadJobs, startPolling, stopPolling]);

  useEffect(() => {
    if (eventsRef.current) {
      eventsRef.current.scrollTop = eventsRef.current.scrollHeight;
    }
  }, [events]);

  const activeJob = useMemo(
    () => jobs.find((j) => j.id === activeJobId) ?? null,
    [jobs, activeJobId]
  );

  const activeReport = activeJob?.report ?? "";
  const activeJobError = activeJob?.error ?? "";
  const visibleError = submitError || activeJobError || jobsError;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) return;

    setSubmitting(true);
    setSubmitError("");
    setEvents(["Queueing job…"]);

    try {
      const job = await createJob(trimmed);
      setQuestion("");
      setActiveJobId(job.id);
      await loadJobs();
      setEvents((prev) => [...prev, `Job created: ${job.id}`]);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : String(err));
      setEvents([]);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Shell>
      <div style={{ maxWidth: "960px" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1.5rem", color: "var(--color-text)" }}>
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
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
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
            disabled={submitting || !question.trim()}
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
            <h2 style={{ fontSize: "0.8rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--color-text-muted)", marginBottom: "0.75rem" }}>
              Queue
            </h2>

            {!hasLoadedOnce && !jobsError ? (
              <div style={{ color: "var(--color-text-muted)", fontSize: "0.875rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Loader2 size={14} className="animate-spin" />
                Loading jobs…
              </div>
            ) : jobs.length === 0 ? (
              <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem" }}>No jobs yet.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.375rem" }}>
                {jobs.map((job) => {
                  const label = job.question ?? job.query ?? "(untitled job)";
                  const icon = statusIcon[job.status as keyof typeof statusIcon] ?? (
                    <Clock size={14} style={{ color: "var(--color-text-muted)" }} />
                  );

                  return (
                    <button
                      key={job.id}
                      onClick={() => {
                        setActiveJobId(job.id);
                        setSubmitError("");
                        setEvents([]);
                      }}
                      style={{
                        display: "flex",
                        alignItems: "flex-start",
                        gap: "0.5rem",
                        padding: "0.625rem 0.75rem",
                        background: activeJobId === job.id ? "oklch(from var(--color-primary) l c h / 0.10)" : "var(--color-surface)",
                        border: `1px solid ${activeJobId === job.id ? "var(--color-primary)" : "var(--color-border)"}`,
                        borderRadius: "var(--radius-md)",
                        textAlign: "left",
                        cursor: "pointer",
                      }}
                    >
                      <span style={{ marginTop: "0.125rem", flexShrink: 0 }}>{icon}</span>
                      <span
                        style={{
                          fontSize: "0.8125rem",
                          color: "var(--color-text)",
                          lineHeight: 1.4,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                          maxWidth: "190px",
                        }}
                        title={label}
                      >
                        {label}
                      </span>
                      <ChevronRight size={13} style={{ marginLeft: "auto", color: "var(--color-text-muted)", flexShrink: 0 }} />
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <div>
            {!activeJobId && !visibleError && (
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
                <p style={{ fontSize: "0.875rem" }}>Submit a question or select a job to inspect its report.</p>
              </div>
            )}

            {events.length > 0 && (
              <div style={{ marginBottom: "1rem" }}>
                <h2 style={{ fontSize: "0.8rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--color-text-muted)", marginBottom: "0.5rem" }}>
                  Activity
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
                  {events.map((ev, i) => (
                    <div key={i} style={{ marginBottom: "0.125rem" }}>
                      <span style={{ color: "var(--color-primary)", marginRight: "0.5rem" }}>›</span>
                      {ev}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeJob && (
              <div style={{ marginBottom: "1rem", color: "var(--color-text-muted)", fontSize: "0.875rem" }}>
                Status: <span style={{ color: "var(--color-text)" }}>{activeJob.status}</span>
              </div>
            )}

            {visibleError && (
              <div
                style={{
                  background: "rgba(161, 44, 123, 0.10)",
                  border: "1px solid rgba(161, 44, 123, 0.30)",
                  borderRadius: "var(--radius-md)",
                  padding: "0.75rem 1rem",
                  marginBottom: "1rem",
                  color: "#d163a7",
                  fontSize: "0.875rem",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                }}
              >
                {visibleError}
              </div>
            )}

            {activeReport && (
              <div>
                <h2 style={{ fontSize: "0.8rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--color-text-muted)", marginBottom: "0.5rem" }}>
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
                  <ReactMarkdown>{activeReport}</ReactMarkdown>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </Shell>
  );
}
