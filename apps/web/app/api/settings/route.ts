const API_BASE = process.env.API_ORIGIN ?? "http://axiom-api:7200";

export async function GET() {
  const res = await fetch(`${API_BASE}/settings`, { cache: "no-store" });
  const text = await res.text();
  return new Response(text, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
}

export async function PATCH(req: Request) {
  const body = await req.text();
  const res = await fetch(`${API_BASE}/settings`, {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body,
  });
  const text = await res.text();
  return new Response(text, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
}
