import { fetchUpstream } from "@/lib/server-api";

export async function GET() {
  return fetchUpstream("/health");
}
