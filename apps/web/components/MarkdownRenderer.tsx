"use client";

import ReactMarkdown from "react-markdown";

export default function MarkdownRenderer({ content }: { content: string }) {
  return (
    <div
      style={{
        color: "var(--color-text)",
        fontSize: "0.95rem",
      }}
    >
      <ReactMarkdown
        components={{
          h1: ({ children }) => (
            <h1 style={{ fontSize: "1.65rem", fontWeight: 700, margin: "0 0 1rem" }}>{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 style={{ fontSize: "1.25rem", fontWeight: 700, margin: "1.5rem 0 0.75rem" }}>{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 style={{ fontSize: "1.05rem", fontWeight: 700, margin: "1.25rem 0 0.5rem" }}>{children}</h3>
          ),
          p: ({ children }) => (
            <p style={{ margin: "0 0 0.9rem", whiteSpace: "pre-wrap" }}>{children}</p>
          ),
          ul: ({ children }) => (
            <ul style={{ margin: "0 0 1rem 1.2rem", listStyle: "disc" }}>{children}</ul>
          ),
          ol: ({ children }) => (
            <ol style={{ margin: "0 0 1rem 1.2rem", listStyle: "decimal" }}>{children}</ol>
          ),
          li: ({ children }) => (
            <li style={{ marginBottom: "0.35rem" }}>{children}</li>
          ),
          code: ({ children }) => (
            <code
              style={{
                background: "var(--color-surface-2)",
                border: "1px solid var(--color-border)",
                borderRadius: "0.35rem",
                padding: "0.1rem 0.3rem",
                fontSize: "0.9em",
              }}
            >
              {children}
            </code>
          ),
          pre: ({ children }) => (
            <pre
              style={{
                background: "var(--color-surface-2)",
                border: "1px solid var(--color-border)",
                borderRadius: "0.75rem",
                padding: "0.9rem 1rem",
                overflowX: "auto",
                margin: "0 0 1rem",
              }}
            >
              {children}
            </pre>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noreferrer"
              style={{
                color: "var(--color-primary)",
                textDecoration: "underline",
                textUnderlineOffset: "0.18em",
              }}
            >
              {children}
            </a>
          ),
          blockquote: ({ children }) => (
            <blockquote
              style={{
                margin: "0 0 1rem",
                padding: "0.75rem 1rem",
                borderLeft: "3px solid var(--color-primary)",
                background: "var(--color-surface-2)",
                borderRadius: "0 0.75rem 0.75rem 0",
              }}
            >
              {children}
            </blockquote>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
