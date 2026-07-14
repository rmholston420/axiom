const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:7200";

export async function GET(
  _req: Request,
  ctx: { params: Promise<{ id: string }> }
) {
  const { id } = await ctx.params;
  const upstream = await fetch(`${API_BASE}/jobs/${id}/stream`, {
    headers: { Accept: "text/event-stream" },
    cache: "no-store",
  });

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "content-type": "text/event-stream",
      "cache-control": "no-cache, no-transform",
      connection: "keep-alive",
    },
  });
}
