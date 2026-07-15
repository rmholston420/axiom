import { fetchUpstream, forwardJsonBody } from "@/lib/server-api";

export async function GET(req: Request) {
  const search = new URL(req.url).search;
  return fetchUpstream("/settings", undefined, search);
}

export async function PATCH(req: Request) {
  return forwardJsonBody(req, "/settings", "PATCH");
}
