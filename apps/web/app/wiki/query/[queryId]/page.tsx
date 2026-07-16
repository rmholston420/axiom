import MarkdownRenderer from "@/components/MarkdownRenderer";
import Shell from "@/components/Shell";
import { API_BASE } from "@/lib/api";

type WikiPagePayload = {
  page_id: string;
  page_type: string;
  title: string;
  slug: string;
  markdown: string;
  content_hash: string;
  version: number;
  generated_at: string;
};

async function fetchWikiPage(queryId: string): Promise<WikiPagePayload | null> {
  const pageId = `query:${queryId}`;
  const base =
    typeof window === "undefined"
      ? (process.env.API_ORIGIN ?? "http://axiom-api:7200")
      : API_BASE;

  const url = base.startsWith("http")
    ? `${base}/wiki/pages/${encodeURIComponent(pageId)}`
    : `${base}/wiki/pages/${encodeURIComponent(pageId)}`;

  const res = await fetch(url, { cache: "no-store" }).catch(() => null);
  if (!res || !res.ok) return null;
  return (await res.json()) as WikiPagePayload;
}

export default async function WikiQueryPage({
  params,
}: {
  params: Promise<{ queryId: string }>;
}) {
  const { queryId } = await params;
  const data = await fetchWikiPage(queryId);

  return (
    <Shell>
      <div style={{ display: "grid", gap: "1rem" }}>
        <div
          style={{
            display: "grid",
            gap: "0.4rem",
            padding: "1rem",
            borderRadius: "1rem",
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
          }}
        >
          <div style={{ color: "var(--color-text-muted)", fontSize: "0.9rem" }}>
            Wiki topic
          </div>
          <h1 style={{ margin: 0 }}>{data?.title ?? "Topic not found"}</h1>
          {data ? (
            <div style={{ color: "var(--color-text-muted)", fontSize: "0.9rem" }}>
              {data.page_id} · v{data.version} · {data.generated_at}
            </div>
          ) : null}
        </div>

        <div
          style={{
            padding: "1.25rem",
            borderRadius: "1rem",
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
          }}
        >
          {data ? (
            <MarkdownRenderer content={data.markdown} />
          ) : (
            <p style={{ margin: 0 }}>
              No wiki page exists yet for this query. Generate it from the API first.
            </p>
          )}
        </div>
      </div>
    </Shell>
  );
}
