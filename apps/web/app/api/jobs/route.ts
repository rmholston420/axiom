import { fetchUpstream, forwardJsonBody } from "@/lib/server-api";

export async function GET(req: Request) {
  const search = new URL(req.url).search;
  return fetchUpstream("/jobs", undefined, search);
}

export async function POST(req: Request) {
  return forwardJsonBody(req, "/jobs", "POST");
}
