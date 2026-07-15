import { forwardJsonBody } from "@/lib/server-api";

export async function POST(req: Request) {
  return forwardJsonBody(req, "/council", "POST");
}
