import { NextRequest, NextResponse } from "next/server";

const API_ORIGIN = process.env.API_ORIGIN ?? "http://axiom-api:7200";

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ pageId: string }> },
) {
  const { pageId } = await context.params;
  const decodedPageId = decodeURIComponent(pageId);

  const res = await fetch(
    `${API_ORIGIN}/wiki/pages/${encodeURIComponent(decodedPageId)}`,
    { cache: "no-store" },
  );

  const text = await res.text();
  return new NextResponse(text, {
    status: res.status,
    headers: {
      "content-type": res.headers.get("content-type") ?? "application/json",
    },
  });
}
