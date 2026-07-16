import { buildUpstreamUrl } from "@/lib/server-api";

export async function GET(
  req: Request,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const search = new URL(req.url).search;
  const upstreamUrl = buildUpstreamUrl(`/jobs/${encodeURIComponent(id)}/stream`, search);

  const upstream = await fetch(upstreamUrl, {
    method: "GET",
    cache: "no-store",
    headers: {
      accept: "text/event-stream",
    },
  });

  if (!upstream.ok || !upstream.body) {
    const text = await upstream.text();
    return new Response(
      text || JSON.stringify({ error: "Upstream SSE unavailable", upstream: upstreamUrl }),
      {
        status: upstream.status || 502,
        headers: {
          "content-type": upstream.headers.get("content-type") || "application/json; charset=utf-8",
          "cache-control": "no-store",
        },
      },
    );
  }

  const headers = new Headers();
  headers.set("content-type", upstream.headers.get("content-type") || "text/event-stream; charset=utf-8");
  headers.set("cache-control", "no-cache, no-store, must-revalidate");
  headers.set("x-accel-buffering", "no");

  return new Response(upstream.body, {
    status: upstream.status,
    headers,
  });
}
