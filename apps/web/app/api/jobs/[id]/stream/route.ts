import { buildUpstreamUrl, getApiOrigin } from "@/lib/server-api";

const REQUEST_TIMEOUT_MS = 90000;

export async function GET(
  req: Request,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const search = new URL(req.url).search;
  const upstreamUrl = buildUpstreamUrl(`/jobs/${encodeURIComponent(id)}/stream`, search);

  console.log("[stream] apiOrigin", getApiOrigin());
  console.log("[stream] upstreamUrl", upstreamUrl);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const upstream = await fetch(upstreamUrl, {
      method: "GET",
      cache: "no-store",
      signal: controller.signal,
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
    headers.set("cache-control", "no-cache, no-transform");
    headers.set("connection", "keep-alive");
    headers.set("x-accel-buffering", "no");

    return new Response(upstream.body, {
      status: upstream.status,
      headers,
    });
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    const status =
      error instanceof Error && error.name === "AbortError" ? 504 : 502;

    return Response.json(
      {
        error: status === 504 ? "Upstream SSE timeout" : "Upstream SSE unreachable",
        upstream: upstreamUrl,
        apiOrigin: getApiOrigin(),
        detail,
      },
      { status },
    );
  } finally {
    clearTimeout(timeout);
  }
}
