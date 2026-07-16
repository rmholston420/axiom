type Source = {
  title: string;
  url: string;
  snippet?: string;
};

export default function SourcesPanel({
  title,
  sources,
}: {
  title: string;
  sources: Source[];
}) {
  if (!sources.length) return null;

  return (
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
        {title}
      </h2>

      <div
        style={{
          display: "grid",
          gap: "0.6rem",
        }}
      >
        {sources.map((source, index) => (
          <a
            key={`${source.url}-${index}`}
            href={source.url}
            target="_blank"
            rel="noreferrer"
            style={{
              display: "block",
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-lg)",
              padding: "0.85rem 1rem",
              textDecoration: "none",
              color: "var(--color-text)",
            }}
          >
            <div
              style={{
                fontSize: "0.92rem",
                fontWeight: 600,
                marginBottom: source.snippet ? "0.35rem" : 0,
                wordBreak: "break-word",
              }}
            >
              {source.title || source.url}
            </div>

            <div
              style={{
                fontSize: "0.78rem",
                color: "var(--color-primary)",
                marginBottom: source.snippet ? "0.35rem" : 0,
                wordBreak: "break-all",
              }}
            >
              {source.url}
            </div>

            {source.snippet && (
              <div
                style={{
                  fontSize: "0.82rem",
                  color: "var(--color-text-muted)",
                  lineHeight: 1.5,
                }}
              >
                {source.snippet}
              </div>
            )}
          </a>
        ))}
      </div>
    </div>
  );
}
