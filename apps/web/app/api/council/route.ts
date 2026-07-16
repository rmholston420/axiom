import { forwardJsonBody } from "@/lib/server-api";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 300;

export async function POST(req: Request) {
  return forwardJsonBody(req, "/council", "POST", 290000);
}
