import { fetchUpstream } from "@/lib/server-api";

export async function GET(
  req: Request,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const search = new URL(req.url).search;
  return fetchUpstream(`/jobs/${encodeURIComponent(id)}`, undefined, search);
}
