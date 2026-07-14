const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:7200";

export async function GET() {
  const res = await fetch(`${API_BASE}/jobs`, { cache: "no-store" });
  const text = await res.text();
  return new Response(text, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
}

export async function POST(req: Request) {
  const body = await req.text();
  const res = await fetch(`${API_BASE}/jobs`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body,
  });
  const text = await res.text();
  return new Response(text, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
}
