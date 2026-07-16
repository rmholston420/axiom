import { fetchUpstream } from "@/lib/server-api";

export async function PATCH(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const body = await req.text();
  return fetchUpstream(
    `/axiomatizer/axioms/${id}/approve`,
    { method: "PATCH", body, headers: { "Content-Type": "application/json" } },
  );
}
