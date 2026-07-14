"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  CheckCircle2,
  ChevronRight,
  Clock,
  Loader2,
  Send,
  XCircle,
  Zap,
} from "lucide-react";
import Shell from "@/components/Shell";
import { API_BASE, createJob, fetchJobs, type Job } from "@/lib/api";

const panelStyle: React.CSSProperties = {
  background: "var(--color-surface)",
  border: "1px solid var(--color-border)",
  borderRadius: "var(--radius-lg)",
};

function linkifyReportMarkdown(markdown: string): string {
  if (!markdown) return markdown;

  let out = markdown;

  out = out.replace(
    /Retrieved from <(https?:\/\/[^>\s]+)>/g,
    'Retrieved from [$1]($1)'
  );

  out = out.replace(
    /(?<!\]\()(?<!href=")(https?:\/\/[^\s<)]+)(?![^[]*\])/g,
    (url) => `[${url}](${url})`
  );

  return out;
}

function normalizeSseChunk(raw: string): {
  events: string[];
  report?: string;
  error?: string;
  done?: boolean;
} {
  const text = raw.trim();
  if (!text) return { events: [] };
  if (text === "[DONE]") return { events: [], done: true };

  try {
    const parsed = JSON.parse(text);
    const payload =
      parsed && typeof parsed === "object" && parsed.data && typeof parsed.data === "object"
        ? parsed.data
        : parsed;

    const events: string[] = [];

    if (typeof parsed.event === "string") {
      if (typeof payload.status === "string") {
        events.push(`${parsed.event}: ${payload.status}`);
      } else if (typeof payload.message === "string") {
        events.push(`${parsed.event}: ${payload.message}`);
      } else {
        events.push(parsed.event);
      }
    }

    const candidates = [
      payload.message,
      payload.detail,
      payload.status,
      payload.step,
      payload.phase,
      payload.log,
      payload.text,
    ].filter((v): v is string => typeof v === "string" && v.trim().length > 0);

    for (const c of candidates) {
      if (!events.includes(c) && !events.includes(`status: ${c}`)) {
        events.push(c);
      }
    }

    const report =
      typeof payload.report === "string"
        ? payload.report
        : typeof payload.content === "string"
          ? payload.content
          : undefined;

    const error =
      typeof payload.error === "string"
        ? payload.error
        : typeof payload.detail === "string" && parsed.event === "error"
          ? payload.detail
          : undefined;

    const done =
      payload.done === true ||
      payload.complete === true ||
      payload.finished === true ||
      payload.status === "done" ||
      parsed.event === "done";

    return { events, report, error, done };
  } catch {
    return { events: [text] };
  }
}

export default function DashboardPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [query, setQuery] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [events, setEvents] = useState<string[]>([]);
  const [report, setReport] = useState("");
  const [error, setError] = useState("");
  const [apiStatus, setApiStatus] = useState<"unknown" | "ok" | "error">("unknown");
  const [apiMessage, setApiMessage] = useState("");

  const eventSourceRef = useRef<EventSource | null>(null);
  const streamRef = useRef<HTMLDivElement | null>(null);

  const activeJob = useMemo(
    () => jobs.find((job) => job.id === activeJobId) ?? null,
    [jobs, activeJobId]
  );

  const renderedReport = useMemo(() => linkifyReportMarkdown(report), [report]);

  const loadJobs = useCallback(async (silent = false) => {
    try {
      console.log("[dashboard] fetchJobs via", `${API_BASE}/jobs`);
      const data = await fetchJobs();
      setJobs(data);
      setApiStatus("ok");
      setApiMessage(`${API_BASE}/jobs`);

      if (activeJobId) {
        const current = data.find((job) => job.id === activeJobId);
        if (current?.report) setReport(current.report);
        if (current?.error) setError(current.error);
      }
    } catch (err) {
      if (!silent) {
        console.error("[dashboard] Failed to fetch jobs", err);
      }
      setApiStatus("error");
      setApiMessage(err instanceof Error ? err.message : String(err));
    }
  }, [activeJobId]);

  useEffect(() => {
    const kickoff = window.setTimeout(() => {
      void loadJobs(false);
    }, 0);

    const poller = window.setInterval(() => {
      void loadJobs(true);
    }, 2500);

    return () => {
      window.clearTimeout(kickoff);
      window.clearInterval(poller);
    };
  }, [loadJobs]);

  useEffect(() => {
    if (streamRef.current) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight;
    }
  }, [events]);

  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
    };
  }, []);

  const attachStream = useCallback(
    (jobId: string) => {
      eventSourceRef.current?.close();

      const url = `${API_BASE}/jobs/${jobId}/stream`;
      console.log("[dashboard] EventSource via", url);

      const es = new EventSource(url);
      eventSourceRef.current = es;

      es.onopen = () => {
        setEvents((prev) => [...prev, "Stream connected"]);
      };

      es.onmessage = (evt) => {
        const chunk = normalizeSseChunk(evt.data);

        if (chunk.events.length > 0) {
          setEvents((prev) => [...prev, ...chunk.events]);
        }

        if (chunk.report) {
          setReport(chunk.report);
        }

        if (chunk.error) {
          setError(chunk.error);
        }

        if (chunk.done) {
          setEvents((prev) => [...prev, "Stream completed"]);
          es.close();
          void loadJobs(true);
        }
      };

      es.onerror = () => {
        setEvents((prev) => [...prev, "Stream disconnected"]);
        es.close();
        void loadJobs(true);
      };
    },
    [loadJobs]
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;

    setSubmitting(true);
    setError("");
    setReport("");
    setEvents([]);

    try {
      const job = await createJob(trimmed);
      setApiStatus("ok");
      setApiMessage(`${API_BASE}/jobs`);
      setQuery("");
      setActiveJobId(job.id);
      setEvents([`Job queued: ${trimmed}`, `Job ID: ${job.id}`]);
      attachStream(job.id);
      void loadJobs(true);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create job";
      setError(message);
      setApiStatus("error");
      setApiMessage(message);
    } finally {
      setSubmitting(false);
    }
  };

  const selectJob = (job: Job) => {
    setActiveJobId(job.id);
    setError(job.error ?? "");
    setReport(job.report ?? "");
    setEvents([`Selected job: ${job.id}`]);

    if (job.status === "queued" || job.status === "running") {
      attachStream(job.id);
    } else {
      eventSourceRef.current?.close();
    }
  };

  return (
    <Shell>
      <div style={{ display: "grid", gap: "1.5rem" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "0.25rem" }}>
            Dashboard
          </h1>
          <p style={{ color: "var(--color-text-muted)", fontSize: "0.95rem" }}>
            Queue research jobs, watch the live stream, and review final reports.
          </p>
          <div
            style={{
              marginTop: "0.5rem",
              fontSize: "0.85rem",
              color:
                apiStatus === "ok"
                  ? "#86efac"
                  : apiStatus === "error"
                    ? "#fca5a5"
                    : "var(--color-text-muted)",
            }}
          >
            API status: {apiStatus}{apiMessage ? ` — ${apiMessage}` : ""}
          </div>
        </div>

        <form
          onSubmit={handleSubmit}
          style={{
            ...panelStyle,
            padding: "1rem",
            display: "grid",
            gap: "0.75rem",
          }}
        >
          <label htmlFor="query" style={{ fontWeight: 600, fontSize: "0.95rem" }}>
            Research query
          </label>
          <div style={{ display: "flex", gap: "0.75rem" }}>
            <input
              id="query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a research question..."
              style={{
                flex: 1,
                background: "var(--color-surface-2)",
                color: "var(--color-text)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
                padding: "0.8rem 0.9rem",
              }}
            />
            <button
              type="submit"
              disabled={submitting || !query.trim()}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.5rem",
                padding: "0.8rem 1rem",
                background: "var(--color-primary)",
                color: "white",
                border: "none",
                borderRadius: "var(--radius-md)",
                fontWeight: 600,
                opacity: submitting ? 0.7 : 1,
                cursor: submitting ? "not-allowed" : "pointer",
              }}
            >
              {submitting ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
              Run
            </button>
          </div>
        </form>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "320px 1fr",
            gap: "1.5rem",
            alignItems: "start",
          }}
        >
          <section style={{ ...panelStyle, padding: "1rem" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "0.75rem",
              }}
            >
              <h2 style={{ fontSize: "1rem", fontWeight: 700 }}>Queue</h2>
              <button
                onClick={() => void loadJobs(false)}
                style={{
                  fontSize: "0.85rem",
                  color: "var(--color-primary)",
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                }}
              >
                Refresh
              </button>
            </div>

            <div style={{ display: "grid", gap: "0.5rem" }}>
              {jobs.length === 0 ? (
                <div style={{ color: "var(--color-text-muted)", fontSize: "0.9rem" }}>
                  No jobs yet.
                </div>
              ) : (
                jobs.map((job) => {
                  const selected = job.id === activeJobId;
                  const statusIcon =
                    job.status === "done" ? (
                      <CheckCircle2 size={16} />
                    ) : job.status === "error" ? (
                      <XCircle size={16} />
                    ) : job.status === "running" ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      <Clock size={16} />
                    );

                  return (
                    <button
                      key={job.id}
                      onClick={() => selectJob(job)}
                      style={{
                        textAlign: "left",
                        width: "100%",
                        padding: "0.85rem",
                        borderRadius: "var(--radius-md)",
                        border: selected
                          ? "1px solid var(--color-primary)"
                          : "1px solid var(--color-border)",
                        background: selected ? "rgba(79,152,163,0.12)" : "var(--color-surface-2)",
                        color: "var(--color-text)",
                        cursor: "pointer",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "0.5rem",
                          marginBottom: "0.35rem",
                          fontWeight: 600,
                          fontSize: "0.92rem",
                        }}
                      >
                        {statusIcon}
                        <span style={{ textTransform: "capitalize" }}>{job.status}</span>
                        <ChevronRight size={14} style={{ marginLeft: "auto" }} />
                      </div>
                      <div
                        style={{
                          color: "var(--color-text-muted)",
                          fontSize: "0.85rem",
                          lineHeight: 1.4,
                        }}
                      >
                        {job.query || job.question || ""}
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </section>

          <div style={{ display: "grid", gap: "1rem" }}>
            <section style={{ ...panelStyle, padding: "1rem" }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.6rem",
                  marginBottom: "0.75rem",
                }}
              >
                <Zap size={16} />
                <h2 style={{ fontSize: "1rem", fontWeight: 700 }}>Live stream</h2>
              </div>

              <div
                ref={streamRef}
                style={{
                  minHeight: "220px",
                  maxHeight: "320px",
                  overflow: "auto",
                  background: "var(--color-surface-2)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                  padding: "0.9rem",
                  fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
                  fontSize: "0.88rem",
                  lineHeight: 1.6,
                  whiteSpace: "pre-wrap",
                }}
              >
                {events.length === 0 ? (
                  <span style={{ color: "var(--color-text-muted)" }}>
                    {activeJob && (activeJob.status === "running" || activeJob.status === "queued")
                      ? "Waiting for stream events..."
                      : "Select or start a job to view live events."}
                  </span>
                ) : (
                  events.map((line, idx) => (
                    <div key={`${idx}-${line.slice(0, 12)}`} style={{ marginBottom: "0.35rem" }}>
                      {line}
                    </div>
                  ))
                )}
              </div>
            </section>

            <section style={{ ...panelStyle, padding: "1rem" }}>
              <h2 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "0.75rem" }}>
                Final report
              </h2>

              {error ? (
                <div
                  style={{
                    color: "#fda4af",
                    background: "rgba(127,29,29,0.25)",
                    border: "1px solid rgba(248,113,113,0.35)",
                    borderRadius: "var(--radius-md)",
                    padding: "0.85rem",
                  }}
                >
                  {error}
                </div>
              ) : report ? (
                <div
                  style={{
                    background: "var(--color-surface-2)",
                    border: "1px solid var(--color-border)",
                    borderRadius: "var(--radius-md)",
                    padding: "1rem",
                  }}
                >
                  <ReactMarkdown
                    components={{
                      a: ({ href, children }) => (
                        <a
                          href={href}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            color: "var(--color-primary)",
                            textDecoration: "underline",
                            textUnderlineOffset: "2px",
                          }}
                        >
                          {children}
                        </a>
                      ),
                    }}
                  >
                    {renderedReport}
                  </ReactMarkdown>
                </div>
              ) : (
                <div style={{ color: "var(--color-text-muted)", fontSize: "0.9rem" }}>
                  No final report yet.
                </div>
              )}
            </section>
          </div>
        </div>
      </div>
    </Shell>
  );
}
