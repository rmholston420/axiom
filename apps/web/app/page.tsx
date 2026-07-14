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
import { createJob, fetchJobs, type Job } from "@/lib/api";

const panelStyle: React.CSSProperties = {
  background: "var(--color-surface)",
  border: "1px solid var(--color-border)",
  borderRadius: "var(--radius-lg)",
};

export default function DashboardPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [query, setQuery] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [events, setEvents] = useState<string[]>([]);
  const [report, setReport] = useState("");
  const [error, setError] = useState("");
  const streamRef = useRef<EventSource | null>(null);
  const eventsRef = useRef<HTMLDivElement>(null);

  const loadJobs = useCallback(async () => {
    try {
      const data = await fetchJobs();
      const sorted = [...data].sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      );
      setJobs(sorted);
    } catch {
      // leave existing state in place
    }
  }, []);

  useEffect(() => {
    const kick = window.setTimeout(() => {
      void loadJobs();
    }, 0);

    const timer = window.setInterval(() => {
      void loadJobs();
    }, 5000);

    return () => {
      window.clearTimeout(kick);
      window.clearInterval(timer);
    };
  }, [loadJobs]);

  useEffect(() => {
    if (eventsRef.current) {
      eventsRef.current.scrollTop = eventsRef.current.scrollHeight;
    }
  }, [events]);

  useEffect(() => {
    return () => streamRef.current?.close();
  }, []);

  const activeJob = useMemo(
    () => jobs.find((job) => job.id === activeJobId) ?? null,
    [jobs, activeJobId],
  );

  const openStream = useCallback(
    (jobId: string) => {
      streamRef.current?.close();
      setActiveJobId(jobId);
      setEvents([]);
      setReport("");
      setError("");

      const es = new EventSource(`/api/jobs/${jobId}/stream`);
      streamRef.current = es;

      es.onmessage = (event) => {
        const payload = event.data as string;

        if (payload === "[DONE]") {
          es.close();
          void loadJobs();
          return;
        }

        try {
          const parsed = JSON.parse(payload) as
            | { type: "event"; message: string }
            | { type: "report"; content: string }
            | { type: "error"; message: string };

          if (parsed.type === "event") setEvents((prev) => [...prev, parsed.message]);
          if (parsed.type === "report") setReport(parsed.content);
          if (parsed.type === "error") setError(parsed.message);
        } catch {
          setEvents((prev) => [...prev, payload]);
        }
      };

      es.onerror = () => {
        es.close();
        void loadJobs();
      };
    },
    [loadJobs],
  );

  const statusIcon = (status: Job["status"]) => {
    if (status === "queued") return <Clock size={14} color="var(--color-text-muted)" />;
    if (status === "running") return <Loader2 size={14} className="animate-spin" color="var(--color-primary)" />;
    if (status === "done") return <CheckCircle2 size={14} color="var(--color-success)" />;
    return <XCircle size={14} color="var(--color-error)" />;
  };

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!query.trim()) return;

    setSubmitting(true);
    setError("");

    try {
      const job = await createJob(query.trim());
      setQuery("");
      await loadJobs();
      openStream(job.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Shell>
      <div style={{ maxWidth: 1180, margin: "0 auto" }}>
        <h1 style={{ fontSize: "1.6rem", fontWeight: 700, marginBottom: "1.25rem" }}>Dashboard</h1>

        <form
          onSubmit={handleSubmit}
          style={{
            ...panelStyle,
            display: "flex",
            gap: "0.75rem",
            padding: "1rem",
            marginBottom: "1.5rem",
          }}
        >
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a research question…"
            disabled={submitting}
            style={{
              flex: 1,
              background: "var(--color-surface-2)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
              padding: "0.8rem 0.9rem",
              color: "var(--color-text)",
            }}
          />
          <button
            type="submit"
            disabled={submitting || !query.trim()}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.45rem",
              padding: "0.8rem 1.15rem",
              border: "none",
              borderRadius: "var(--radius-md)",
              background: submitting ? "var(--color-border)" : "var(--color-primary)",
              color: "white",
              fontWeight: 600,
            }}
          >
            {submitting ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            {submitting ? "Queuing…" : "Run"}
          </button>
        </form>

        {error && (
          <div
            style={{
              ...panelStyle,
              marginBottom: "1rem",
              padding: "0.85rem 1rem",
              color: "var(--color-error)",
            }}
          >
            {error}
          </div>
        )}

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "300px minmax(0, 1fr)",
            gap: "1.5rem",
            alignItems: "start",
          }}
        >
          <section>
            <div
              style={{
                fontSize: "0.78rem",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                color: "var(--color-text-muted)",
                marginBottom: "0.65rem",
              }}
            >
              Queue
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.45rem" }}>
              {jobs.length === 0 ? (
                <div style={{ ...panelStyle, padding: "1rem", color: "var(--color-text-muted)" }}>
                  No jobs yet.
                </div>
              ) : (
                jobs.map((job) => (
                  <button
                    key={job.id}
                    type="button"
                    onClick={() => {
                      if (job.status === "running" || job.status === "queued") {
                        openStream(job.id);
                      } else {
                        streamRef.current?.close();
                        setActiveJobId(job.id);
                        setEvents([]);
                        setReport(job.report ?? "");
                        setError(job.error ?? "");
                      }
                    }}
                    style={{
                      ...panelStyle,
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "0.55rem",
                      padding: "0.75rem",
                      textAlign: "left",
                      background:
                        activeJobId === job.id
                          ? "color-mix(in oklab, var(--color-primary) 10%, var(--color-surface))"
                          : "var(--color-surface)",
                      border:
                        activeJobId === job.id
                          ? "1px solid var(--color-primary)"
                          : "1px solid var(--color-border)",
                    }}
                  >
                    <span style={{ marginTop: "0.15rem", flexShrink: 0 }}>{statusIcon(job.status)}</span>
                    <span style={{ minWidth: 0, flex: 1 }}>
                      <div
                        style={{
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          fontSize: "0.85rem",
                          fontWeight: 600,
                        }}
                      >
                        {job.query}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>
                        {job.status}
                      </div>
                    </span>
                    <ChevronRight size={14} color="var(--color-text-muted)" />
                  </button>
                ))
              )}
            </div>
          </section>

          <section>
            {!activeJob && !report && events.length === 0 ? (
              <div
                style={{
                  ...panelStyle,
                  minHeight: 320,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--color-text-muted)",
                  gap: "0.75rem",
                }}
              >
                <Zap size={30} style={{ opacity: 0.35 }} />
                <div style={{ fontSize: "0.92rem" }}>
                  Submit a question or select a job to inspect its output.
                </div>
              </div>
            ) : (
              <>
                {(events.length > 0 || activeJob?.status === "running" || activeJob?.status === "queued") && (
                  <div style={{ marginBottom: "1rem" }}>
                    <div
                      style={{
                        fontSize: "0.78rem",
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                        color: "var(--color-text-muted)",
                        marginBottom: "0.65rem",
                      }}
                    >
                      Live Stream
                    </div>
                    <div
                      ref={eventsRef}
                      style={{
                        ...panelStyle,
                        padding: "1rem",
                        maxHeight: 220,
                        overflowY: "auto",
                        fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
                        fontSize: "0.82rem",
                        color: "var(--color-text-muted)",
                      }}
                    >
                      {events.length === 0 ? (
                        <div>Waiting for events…</div>
                      ) : (
                        events.map((line, index) => (
                          <div key={`${index}-${line}`} style={{ marginBottom: "0.3rem" }}>
                            <span style={{ color: "var(--color-primary)", marginRight: "0.45rem" }}>›</span>
                            {line}
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}

                {report && (
                  <div>
                    <div
                      style={{
                        fontSize: "0.78rem",
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                        color: "var(--color-text-muted)",
                        marginBottom: "0.65rem",
                      }}
                    >
                      Report
                    </div>
                    <div style={{ ...panelStyle, padding: "1.35rem 1.5rem" }}>
                      <div className="markdown">
                        <ReactMarkdown>{report}</ReactMarkdown>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </section>
        </div>
      </div>
    </Shell>
  );
}
