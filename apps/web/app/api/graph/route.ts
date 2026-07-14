const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:7200";

export async function GET() {
  const candidates = ["/graph", "/graph/data", "/graphs", "/neo4j/graph"];
  let lastStatus = 404;
  let lastText = '{"detail":"No graph endpoint available on API"}';

  for (const path of candidates) {
    const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
    const text = await res.text();
    if (res.ok) {
      return new Response(text, {
        status: 200,
        headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
      });
    }
    lastStatus = res.status;
    lastText = text;
  }

  return new Response(lastText, {
    status: lastStatus,
    headers: { "content-type": "application/json" },
  });
}
