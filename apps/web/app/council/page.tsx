"use client";

import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  MessageSquareText,
  Scale,
  Users,
  Zap,
} from "lucide-react";
import Shell from "@/components/Shell";
import { runCouncil, type CouncilMode, type CouncilResponse } from "@/lib/api";

const quickPrompts = [
  "What are the strongest arguments for and against local-first AI research systems?",
  "Should a graph-backed research assistant prefer breadth or depth by default?",
  "What are the tradeoffs between sequential and parallel council deliberation?",
];

function fieldStyle(): React.CSSProperties {
  return {
    width: "100%",
    background: "var(--color-surface-2)",
    color: "var(--color-text)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    padding: "0.8rem 0.9rem",
  };
}

function statCard(label: string, value: string | number, color = "var(--color-text)") {
  return (
    <div
      key={label}
      style={{
        padding: "0.9rem 1rem",
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      <div
        style={{
          fontSize: "0.75rem",
          color: "var(--color-text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: "1.25rem",
          fontWeight: 700,
          color,
          marginTop: "0.25rem",
        }}
      >
        {value}
      </div>
    </div>
  );
}

export default function CouncilPage() {
  const [question, setQuestion] = useState(quickPrompts[0]);
  const [context, setContext] = useState("");
  const [mode, setMode] = useState<CouncilMode>("sequential");
  const [councilSize, setCouncilSize] = useState(3);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<CouncilResponse | null>(null);

  const stats = useMemo(() => {
    const outcome = result?.has_disagreement ? "Disagreement" : "Agreement";
    return [
      statCard("Mode", result?.mode ?? mode, "var(--color-primary)"),
      statCard("Members", result?.members.length ?? 0),
      statCard(
        "Outcome",
        result?.consensus ?? outcome,
        result?.has_disagreement ? "var(--color-warning)" : "var(--color-success)",
      ),
    ];
  }, [mode, result]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError("");
    try {
      const response = await runCouncil({
        question: question.trim(),
        context: context.trim(),
        council_size: councilSize,
        mode,
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Shell>
      <div style={{ maxWidth: "1280px", display: "grid", gap: "1rem" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "1rem",
            flexWrap: "wrap",
          }}
        >
          <div>
            <h1
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.65rem",
                fontSize: "1.75rem",
                fontWeight: 700,
                margin: 0,
              }}
            >
              <Users size={22} style={{ color: "var(--color-primary)" }} />
              Council
            </h1>
            <p style={{ color: "var(--color-text-muted)", fontSize: "0.95rem", margin: "0.35rem 0 0" }}>
              Run structured multi-perspective deliberation and synthesize agreement or disagreement.
            </p>
          </div>
          <div style={{ color: "var(--color-text-muted)", fontSize: "0.85rem" }}>
            Uses the Axiom Council proxy at <code>/api/council</code>.
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "0.75rem",
          }}
        >
          {stats}
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(360px, 420px) minmax(0, 1fr)",
            gap: "1rem",
            alignItems: "start",
          }}
        >
          <section
            style={{
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-lg)",
              padding: "1rem",
              position: "sticky",
              top: "1rem",
            }}
          >
            <form onSubmit={onSubmit} style={{ display: "grid", gap: "1rem" }}>
              <div>
                <label style={{ display: "grid", gap: "0.45rem" }}>
                  <span style={{ fontSize: "0.9rem", fontWeight: 600 }}>Question</span>
                  <textarea
                    rows={5}
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Ask the council a substantive question..."
                    style={{ ...fieldStyle(), resize: "vertical", minHeight: "120px" }}
                  />
                </label>
              </div>

              <div>
                <label style={{ display: "grid", gap: "0.45rem" }}>
                  <span style={{ fontSize: "0.9rem", fontWeight: 600 }}>Context (optional)</span>
                  <textarea
                    rows={6}
                    value={context}
                    onChange={(e) => setContext(e.target.value)}
                    placeholder="Provide extra background, constraints, or evidence..."
                    style={{ ...fieldStyle(), resize: "vertical", minHeight: "140px" }}
                  />
                </label>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                <label style={{ display: "grid", gap: "0.45rem" }}>
                  <span style={{ fontSize: "0.9rem", fontWeight: 600 }}>Mode</span>
                  <select
                    value={mode}
                    onChange={(e) => setMode(e.target.value as CouncilMode)}
                    style={fieldStyle()}
                  >
                    <option value="sequential">Sequential</option>
                    <option value="parallel">Parallel</option>
                  </select>
                </label>

                <label style={{ display: "grid", gap: "0.45rem" }}>
                  <span style={{ fontSize: "0.9rem", fontWeight: 600 }}>Council size</span>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={councilSize}
                    onChange={(e) => setCouncilSize(Number(e.target.value))}
                    style={fieldStyle()}
                  />
                </label>
              </div>

              <button
                type="submit"
                disabled={loading || !question.trim()}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "0.5rem",
                  padding: "0.85rem 1rem",
                  background: loading ? "var(--color-border)" : "var(--color-primary)",
                  color: "white",
                  border: "none",
                  borderRadius: "var(--radius-md)",
                  fontWeight: 600,
                  opacity: loading || !question.trim() ? 0.75 : 1,
                  cursor: loading || !question.trim() ? "not-allowed" : "pointer",
                }}
              >
                {loading ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
                {loading ? "Running council..." : "Run council"}
              </button>
            </form>

            <div style={{ marginTop: "1rem", paddingTop: "1rem", borderTop: "1px solid var(--color-divider)" }}>
              <div
                style={{
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  color: "var(--color-text-muted)",
                  marginBottom: "0.75rem",
                }}
              >
                Quick prompts
              </div>
              <div style={{ display: "grid", gap: "0.5rem" }}>
                {quickPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => setQuestion(prompt)}
                    style={{
                      textAlign: "left",
                      padding: "0.75rem 0.875rem",
                      background: "var(--color-surface-2)",
                      border: "1px solid var(--color-border)",
                      borderRadius: "var(--radius-md)",
                      color: "var(--color-text)",
                      fontSize: "0.85rem",
                    }}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          </section>

          <section style={{ display: "grid", gap: "1rem" }}>
            {error ? (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.6rem",
                  padding: "0.9rem 1rem",
                  color: "var(--color-error)",
                  background: "color-mix(in oklab, var(--color-error) 10%, transparent)",
                  border: "1px solid color-mix(in oklab, var(--color-error) 30%, transparent)",
                  borderRadius: "var(--radius-lg)",
                }}
              >
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            ) : null}

            {!result && !loading && !error ? (
              <div
                style={{
                  background: "var(--color-surface)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-lg)",
                  padding: "2rem",
                  color: "var(--color-text-muted)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.75rem" }}>
                  <Scale size={18} style={{ color: "var(--color-primary)" }} />
                  <span style={{ fontSize: "1rem", fontWeight: 600, color: "var(--color-text)" }}>
                    No deliberation yet
                  </span>
                </div>
                Submit a question to generate member opinions and a chairman synthesis.
              </div>
            ) : null}

            {loading ? (
              <div
                style={{
                  background: "var(--color-surface)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-lg)",
                  padding: "1rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                  color: "var(--color-text-muted)",
                }}
              >
                <Loader2 size={18} className="animate-spin" />
                Running council deliberation...
              </div>
            ) : null}

            {result ? (
              <>
                <div
                  style={{
                    background: "var(--color-surface)",
                    border: "1px solid var(--color-border)",
                    borderRadius: "var(--radius-lg)",
                    padding: "1rem",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap", marginBottom: "0.85rem" }}>
                    <h2 style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "1rem", fontWeight: 700, margin: 0 }}>
                      <MessageSquareText size={16} style={{ color: "var(--color-primary)" }} />
                      Chairman synthesis
                    </h2>
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "0.35rem",
                        padding: "0.3rem 0.55rem",
                        borderRadius: "var(--radius-full)",
                        fontSize: "0.75rem",
                        fontWeight: 600,
                        color: result.has_disagreement ? "var(--color-warning)" : "var(--color-success)",
                        background: result.has_disagreement
                          ? "color-mix(in oklab, var(--color-warning) 12%, transparent)"
                          : "color-mix(in oklab, var(--color-success) 12%, transparent)",
                        border: result.has_disagreement
                          ? "1px solid color-mix(in oklab, var(--color-warning) 30%, transparent)"
                          : "1px solid color-mix(in oklab, var(--color-success) 30%, transparent)",
                      }}
                    >
                      {result.has_disagreement ? "Disagreement detected" : "Agreement"}
                    </span>
                  </div>

                  <div style={{ color: "var(--color-text-muted)", fontSize: "0.85rem", marginBottom: "0.85rem" }}>
                    <strong style={{ color: "var(--color-text)" }}>Question:</strong> {result.question}
                  </div>

                  <div
                    className="markdown"
                    style={{
                      background: "var(--color-surface-2)",
                      border: "1px solid var(--color-border)",
                      borderRadius: "var(--radius-md)",
                      padding: "1rem",
                    }}
                  >
                    <ReactMarkdown>{result.chairman_synthesis}</ReactMarkdown>
                  </div>
                </div>

                <div style={{ display: "grid", gap: "0.75rem" }}>
                  {result.members.map((member) => (
                    <article
                      key={`${member.member_id}-${member.role}`}
                      style={{
                        background: "var(--color-surface)",
                        border: "1px solid var(--color-border)",
                        borderRadius: "var(--radius-lg)",
                        padding: "1rem",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap", marginBottom: "0.75rem" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                          <div
                            style={{
                              width: "2rem",
                              height: "2rem",
                              borderRadius: "50%",
                              display: "grid",
                              placeItems: "center",
                              background: "color-mix(in oklab, var(--color-primary) 14%, transparent)",
                              color: "var(--color-primary)",
                              fontWeight: 700,
                              fontSize: "0.85rem",
                            }}
                          >
                            {member.member_id}
                          </div>
                          <div>
                            <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--color-text)" }}>
                              {member.role}
                            </div>
                            <div style={{ fontSize: "0.78rem", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                              Council member
                            </div>
                          </div>
                        </div>

                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "0.35rem",
                            padding: "0.25rem 0.5rem",
                            borderRadius: "var(--radius-full)",
                            fontSize: "0.72rem",
                            fontWeight: 600,
                            color: "var(--color-primary)",
                            background: "color-mix(in oklab, var(--color-primary) 10%, transparent)",
                            border: "1px solid color-mix(in oklab, var(--color-primary) 28%, transparent)",
                          }}
                        >
                          <CheckCircle2 size={12} />
                          Opinion captured
                        </span>
                      </div>

                      <div className="markdown">
                        <ReactMarkdown>{member.opinion}</ReactMarkdown>
                      </div>
                    </article>
                  ))}
                </div>
              </>
            ) : null}
          </section>
        </div>
      </div>
    </Shell>
  );
}
