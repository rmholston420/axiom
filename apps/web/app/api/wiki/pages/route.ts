import { fetchUpstream } from "@/lib/server-api";

export async function GET(request: Request) {
  const search = new URL(request.url).search;
  return fetchUpstream("/wiki/pages", undefined, search);
}
