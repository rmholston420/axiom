import { fetchUpstream } from "@/lib/server-api";

export async function GET(req: Request) {
  const search = new URL(req.url).search;
  return fetchUpstream("/graph", undefined, search);
}
