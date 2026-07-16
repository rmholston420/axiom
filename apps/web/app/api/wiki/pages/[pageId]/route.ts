import { NextResponse } from "next/server";

const API_ORIGIN = process.env.API_ORIGIN ?? "http://axiom-api:7200";

export async function GET(
  _request: Request,
  { params }: { params: { pageId: string } },
) {
  const pageId = decodeURIComponent(params.pageId);
  const res = await fetch(`${API_ORIGIN}/wiki/pages/${encodeURIComponent(pageId)}`, {
    cache: "no-store",
  });

  const text = await res.text();
  return new NextResponse(text, {
    status: res.status,
    headers: {
      "content-type": res.headers.get("content-type") ?? "application/json",
    },
  });
}
